use axum::{
    extract::Json,
    http::{StatusCode, Method},
    response::{Response, IntoResponse},
    routing::{get, post},
    Router,
};
use futures::stream::StreamExt;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio_stream::wrappers::ReceiverStream;
use tower_http::cors::{CorsLayer, Any};

#[derive(Debug, Deserialize)]
struct QuestionRequest {
    question: String,
}

#[derive(Debug, Serialize)]
struct OllamaRequest {
    model: String,
    prompt: String,
    stream: bool,
}

#[derive(Debug, Deserialize)]
struct OllamaResponse {
    response: String,
    done: bool,
}

#[derive(Debug, Serialize)]
struct StreamResponse {
    #[serde(rename = "type")]
    response_type: String,
    content: String,
    done: bool,
}

// Простой HTTP ответ для non-streaming
async fn ask_ollama(Json(payload): Json<QuestionRequest>) -> impl IntoResponse {
    println!("📝 Получен вопрос: {}", payload.question);
    
    match query_ollama(&payload.question, false).await {
        Ok(response) => {
            let result = StreamResponse {
                response_type: "complete".to_string(),
                content: response,
                done: true,
            };
            Json(result).into_response()
        }
        Err(e) => {
            eprintln!("❌ Ошибка Ollama: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Ollama error: {}", e)).into_response()
        }
    }
}

// Streaming ответ для максимальной скорости
async fn ask_ollama_stream(Json(payload): Json<QuestionRequest>) -> impl IntoResponse {
    println!("📝 Получен streaming вопрос: {}", payload.question);
    
    let (tx, rx) = tokio::sync::mpsc::channel(100);
    
    // Запускаем streaming в отдельной задаче
    tokio::spawn(async move {
        match stream_ollama_response(&payload.question, tx).await {
            Ok(_) => println!("✅ Streaming завершен успешно"),
            Err(e) => eprintln!("❌ Ошибка streaming: {}", e),
        }
    });
    
    // Возвращаем SSE stream
    let stream = ReceiverStream::new(rx).map(|item| {
        Ok::<_, axum::Error>(format!("data: {}\n\n", item))
    });

    Response::builder()
        .header("content-type", "text/event-stream")
        .header("cache-control", "no-cache")
        .header("connection", "keep-alive")
        .body(axum::body::Body::from_stream(stream))
        .unwrap()
}

async fn query_ollama(question: &str, stream: bool) -> Result<String, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    
    let request = OllamaRequest {
        model: "deepseek-coder-v2".to_string(),
        prompt: format!(
            "Ты эксперт-программист и помощник для технических собеседований. Отвечай четко, структурированно и с примерами кода когда это уместно.\n\nВопрос: {}",
            question
        ),
        stream,
    };

    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&request)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(format!("Ollama API error: {}", response.status()).into());
    }

    if stream {
        // Для streaming будем обрабатывать отдельно
        Ok("streaming".to_string())
    } else {
        let text = response.text().await?;
        if let Ok(ollama_resp) = serde_json::from_str::<OllamaResponse>(&text) {
            Ok(ollama_resp.response)
        } else {
            Ok(text)
        }
    }
}

async fn stream_ollama_response(
    question: &str,
    tx: tokio::sync::mpsc::Sender<String>,
) -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    
    let request = OllamaRequest {
        model: "deepseek-coder-v2".to_string(),
        prompt: format!(
            "Ты эксперт-программист и помощник для технических собеседований. Отвечай четко, структурированно и с примерами кода когда это уместно.\n\nВопрос: {}",
            question
        ),
        stream: true,
    };

    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&request)
        .send()
        .await?;

    if !response.status().is_success() {
        let error_msg = serde_json::to_string(&StreamResponse {
            response_type: "error".to_string(),
            content: format!("Ollama API error: {}", response.status()),
            done: true,
        })?;
        let _ = tx.send(error_msg).await;
        return Ok(());
    }

    let mut stream = response.bytes_stream();
    let mut buffer = String::new();
    let mut full_response = String::new();

    while let Some(chunk_result) = StreamExt::next(&mut stream).await {
        let chunk = chunk_result?;
        buffer.push_str(&String::from_utf8_lossy(&chunk));
        
        // Обрабатываем построчно
        while let Some(newline_pos) = buffer.find('\n') {
            let line = buffer[..newline_pos].trim().to_string();
            buffer = buffer[newline_pos + 1..].to_string();
            
            if line.is_empty() {
                continue;
            }
            
            if let Ok(ollama_resp) = serde_json::from_str::<OllamaResponse>(&line) {
                if !ollama_resp.response.is_empty() {
                    // Отправляем каждый chunk целиком без разбивки на слова
                    full_response.push_str(&ollama_resp.response);
                    
                    let word_response = serde_json::to_string(&StreamResponse {
                        response_type: "word".to_string(),
                        content: ollama_resp.response.clone(),
                        done: false,
                    })?;
                    
                    if tx.send(word_response).await.is_err() {
                        return Ok(()); // Клиент отключился
                    }
                    
                    // Небольшая пауза для плавности
                    tokio::time::sleep(tokio::time::Duration::from_millis(15)).await;
                }
                
                if ollama_resp.done {
                    let done_response = serde_json::to_string(&StreamResponse {
                        response_type: "done".to_string(),
                        content: full_response.trim().to_string(),
                        done: true,
                    })?;
                    
                    let _ = tx.send(done_response).await;
                    break;
                }
            }
        }
    }
    
    Ok(())
}

async fn health() -> impl IntoResponse {
    let current_time = chrono::Utc::now().to_rfc3339();
    let mut status = HashMap::new();
    status.insert("status".to_string(), "ok".to_string());
    status.insert("service".to_string(), "ollama-rust".to_string());
    status.insert("time".to_string(), current_time);
    Json(status)
}

#[tokio::main]
async fn main() {
    println!("🦀 Ollama Rust Service");
    println!("⚡ Максимальная производительность!");
    
    // Настраиваем CORS для Python клиента
    let cors = CorsLayer::new()
        .allow_methods([Method::GET, Method::POST])
        .allow_headers(Any)
        .allow_origin(Any);

    let app = Router::new()
        .route("/health", get(health))
        .route("/ask", post(ask_ollama))
        .route("/stream", post(ask_ollama_stream))
        .layer(cors);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3030")
        .await
        .unwrap();
    
    println!("🚀 Сервер запущен на http://127.0.0.1:3030");
    println!("📊 Health: http://127.0.0.1:3030/health");
    println!("💬 Ask: POST http://127.0.0.1:3030/ask");
    println!("🌊 Stream: POST http://127.0.0.1:3030/stream");

    axum::serve(listener, app).await.unwrap();
} 