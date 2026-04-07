---
name: rust-async-patterns
description: Master Rust async programming with Tokio, async traits, error handling, and concurrent patterns. Use when building async Rust applications, implementing concurrent systems, or debugging async code.
---

# Rust Async Patterns

Production patterns for async Rust programming with Tokio runtime, including tasks, channels, streams, and error handling.

## When to Use This Skill

- Building async Rust applications
- Implementing concurrent network services
- Using Tokio for async I/O
- Handling async errors properly
- Debugging async code issues
- Optimizing async performance

## Core Concepts

### 1. Async Execution Model

```
Future (lazy) → poll() → Ready(value) | Pending
                ↑           ↓
              Waker ← Runtime schedules
```

### 2. Key Abstractions

| Concept    | Purpose                                  |
| ---------- | ---------------------------------------- |
| `Future`   | Lazy computation that may complete later |
| `async fn` | Function returning impl Future           |
| `await`    | Suspend until future completes           |
| `Task`     | Spawned future running concurrently      |
| `Runtime`  | Executor that polls futures              |

## Quick Start

```toml
# Cargo.toml
[dependencies]
tokio = { version = "1", features = ["full"] }
futures = "0.3"
async-trait = "0.1"
anyhow = "1.0"
tracing = "0.1"
tracing-subscriber = "0.3"
```

```rust
use tokio::time::{sleep, Duration};
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    let result = fetch_data("https://api.example.com").await?;
    println!("Got: {}", result);
    Ok(())
}

async fn fetch_data(url: &str) -> Result<String> {
    sleep(Duration::from_millis(100)).await;
    Ok(format!("Data from {}", url))
}
```

## Patterns

### Pattern 1: Concurrent Task Execution

```rust
use tokio::task::JoinSet;
use futures::stream::{self, StreamExt};

async fn fetch_all_concurrent(urls: Vec<String>) -> Result<Vec<String>> {
    let mut set = JoinSet::new();
    for url in urls {
        set.spawn(async move { fetch_data(&url).await });
    }
    let mut results = Vec::new();
    while let Some(res) = set.join_next().await {
        match res {
            Ok(Ok(data)) => results.push(data),
            Ok(Err(e)) => tracing::error!("Task failed: {}", e),
            Err(e) => tracing::error!("Join error: {}", e),
        }
    }
    Ok(results)
}

async fn fetch_with_limit(urls: Vec<String>, limit: usize) -> Vec<Result<String>> {
    stream::iter(urls)
        .map(|url| async move { fetch_data(&url).await })
        .buffer_unordered(limit)
        .collect()
        .await
}
```

### Pattern 2: Channels for Communication

```rust
use tokio::sync::{mpsc, broadcast, oneshot, watch};

async fn mpsc_example() {
    let (tx, mut rx) = mpsc::channel::<String>(100);
    let tx2 = tx.clone();
    tokio::spawn(async move { tx2.send("Hello".to_string()).await.unwrap(); });
    while let Some(msg) = rx.recv().await {
        println!("Got: {}", msg);
    }
}
```

### Pattern 3: Async Error Handling

```rust
use anyhow::{Context, Result};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ServiceError {
    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Timeout after {0:?}")]
    Timeout(std::time::Duration),
}

async fn process_request(id: &str) -> Result<Response> {
    let data = fetch_data(id).await.context("Failed to fetch data")?;
    let parsed = parse_response(&data).context("Failed to parse response")?;
    Ok(parsed)
}
```

### Pattern 4: Graceful Shutdown

```rust
use tokio::signal;
use tokio_util::sync::CancellationToken;

async fn run_server() -> Result<()> {
    let token = CancellationToken::new();
    let token_clone = token.clone();
    tokio::spawn(async move {
        loop {
            tokio::select! {
                _ = token_clone.cancelled() => { break; }
                _ = do_work() => {}
            }
        }
    });
    signal::ctrl_c().await?;
    token.cancel();
    Ok(())
}
```

### Pattern 5: Async Traits

```rust
use async_trait::async_trait;

#[async_trait]
pub trait Repository {
    async fn get(&self, id: &str) -> Result<Entity>;
    async fn save(&self, entity: &Entity) -> Result<()>;
}
```

### Pattern 6: Streams

```rust
use async_stream::stream;
use futures::stream::{Stream, StreamExt};

fn numbers_stream() -> impl Stream<Item = i32> {
    stream! {
        for i in 0..10 {
            tokio::time::sleep(Duration::from_millis(100)).await;
            yield i;
        }
    }
}
```

### Pattern 7: Resource Management

```rust
use tokio::sync::{RwLock, Semaphore};

struct Cache {
    data: RwLock<HashMap<String, String>>,
}

impl Cache {
    async fn get(&self, key: &str) -> Option<String> {
        self.data.read().await.get(key).cloned()
    }
    async fn set(&self, key: String, value: String) {
        self.data.write().await.insert(key, value);
    }
}
```

## Best Practices

### Do's

- **Use `tokio::select!`** for racing futures
- **Prefer channels** over shared state when possible
- **Use `JoinSet`** for managing multiple tasks
- **Instrument with tracing** for debugging async code
- **Handle cancellation** with `CancellationToken`

### Don'ts

- **Don't block** — never use `std::thread::sleep` in async
- **Don't hold locks across awaits** — causes deadlocks
- **Don't spawn unboundedly** — use semaphores for limits
- **Don't ignore errors** — propagate with `?` or log
- **Don't forget Send bounds** for spawned futures
