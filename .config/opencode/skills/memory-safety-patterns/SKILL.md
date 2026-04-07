---
name: memory-safety-patterns
description: Implement memory-safe programming with RAII, ownership, smart pointers, and resource management across Rust, C++, and C. Use when writing safe systems code, managing resources, or preventing memory bugs.
---

# Memory Safety Patterns

Cross-language patterns for memory-safe programming including RAII, ownership, smart pointers, and resource management.

## When to Use This Skill

- Writing memory-safe systems code (especially Rust)
- Managing resources (files, sockets, memory)
- Preventing use-after-free and leaks
- Implementing RAII patterns
- Debugging memory issues

## Core Concepts

### Memory Bug Categories

| Bug Type             | Description                      | Prevention        |
| -------------------- | -------------------------------- | ----------------- |
| **Use-after-free**   | Access freed memory              | Ownership, RAII   |
| **Double-free**      | Free same memory twice           | Smart pointers    |
| **Memory leak**      | Never free memory                | RAII, GC          |
| **Buffer overflow**  | Write past buffer end            | Bounds checking   |
| **Dangling pointer** | Pointer to freed memory          | Lifetime tracking |
| **Data race**        | Concurrent unsynchronized access | Ownership, Sync   |

## Rust Ownership Patterns

### Move Semantics

```rust
fn move_example() {
    let s1 = String::from("hello");
    let s2 = s1; // s1 is MOVED, no longer valid
    println!("{}", s2);
}
```

### Borrowing

```rust
fn borrow_example() {
    let s = String::from("hello");
    let len = calculate_length(&s); // Immutable borrow
    println!("{} has length {}", s, len);

    let mut s = String::from("hello");
    change(&mut s); // Mutable borrow (only one allowed)
}

fn calculate_length(s: &String) -> usize { s.len() }
fn change(s: &mut String) { s.push_str(", world"); }
```

### Lifetimes

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

struct ImportantExcerpt<'a> {
    part: &'a str,
}
```

### Interior Mutability

```rust
use std::cell::{Cell, RefCell};
use std::rc::Rc;

struct Stats {
    count: Cell<i32>,
    data: RefCell<Vec<String>>,
}

impl Stats {
    fn increment(&self) { self.count.set(self.count.get() + 1); }
    fn add_data(&self, item: String) { self.data.borrow_mut().push(item); }
}
```

### Shared Ownership

```rust
use std::sync::Arc;
use std::thread;

fn arc_example() {
    let data = Arc::new(vec![1, 2, 3]);
    let handles: Vec<_> = (0..3).map(|_| {
        let data = Arc::clone(&data);
        thread::spawn(move || println!("{:?}", data))
    }).collect();
    for handle in handles { handle.join().unwrap(); }
}
```

### Thread-Safe State

```rust
use std::sync::{Arc, Mutex, RwLock};
use std::sync::atomic::{AtomicI32, Ordering};

// Atomic for simple types
let counter = Arc::new(AtomicI32::new(0));
counter.fetch_add(1, Ordering::SeqCst);

// Mutex for complex types
let data = Arc::new(Mutex::new(vec![]));
data.lock().unwrap().push(42);

// RwLock for read-heavy workloads
let map = Arc::new(RwLock::new(HashMap::new()));
let _read = map.read().unwrap();  // Multiple readers
let _write = map.write().unwrap(); // Exclusive writer
```

### Bounds Checking

```rust
fn rust_bounds_checking() {
    let vec = vec![1, 2, 3, 4, 5];

    // Panics if out of bounds
    let val = vec[2];

    // Returns Option (no panic)
    match vec.get(10) {
        Some(val) => println!("Got {}", val),
        None => println!("Index out of bounds"),
    }

    // Slices are bounds-checked
    let slice = &vec[1..3]; // [2, 3]
}
```

## Debugging Tools

```bash
# Rust Miri (undefined behavior detector)
cargo +nightly miri run

# AddressSanitizer
RUSTFLAGS="-Z sanitizer=address" cargo +nightly run

# ThreadSanitizer
RUSTFLAGS="-Z sanitizer=thread" cargo +nightly run
```

## Best Practices

### Do's

- **Prefer RAII** — tie resource lifetime to scope
- **Use Arc/Rc** instead of raw pointers
- **Understand ownership** — know who owns what
- **Check bounds** — use safe access methods (`.get()`)
- **Minimize `unsafe`** — isolate and document any unsafe blocks

### Don'ts

- **Don't use raw pointers** unless interfacing with C FFI
- **Don't return local references** — dangling pointer
- **Don't ignore compiler warnings** — they catch bugs
- **Don't use `unsafe` carelessly** — minimize and review thoroughly
- **Don't assume thread safety** — be explicit with `Send`/`Sync`
