---
name: typescript-advanced-types
description: Master TypeScript's advanced type system including generics, conditional types, mapped types, template literals, and utility types for building type-safe applications. Use when implementing complex type logic, creating reusable type utilities, or ensuring compile-time type safety in TypeScript projects.
---

# TypeScript Advanced Types

Comprehensive guidance for mastering TypeScript's advanced type system including generics, conditional types, mapped types, template literal types, and utility types for building robust, type-safe applications.

## When to Use This Skill

- Building type-safe libraries or frameworks
- Creating reusable generic components
- Implementing complex type inference logic
- Designing type-safe API clients (e.g. MCP servers)
- Building form validation systems
- Migrating JavaScript codebases to TypeScript

## Core Concepts

### 1. Generics

```typescript
function identity<T>(value: T): T {
  return value;
}

interface HasLength {
  length: number;
}
function logLength<T extends HasLength>(item: T): T {
  console.log(item.length);
  return item;
}

function merge<T, U>(obj1: T, obj2: U): T & U {
  return { ...obj1, ...obj2 };
}
```

### 2. Conditional Types

```typescript
type IsString<T> = T extends string ? true : false;

type ReturnType<T> = T extends (...args: any[]) => infer R ? R : never;

type TypeName<T> = T extends string
  ? "string"
  : T extends number
    ? "number"
    : T extends boolean
      ? "boolean"
      : "object";
```

### 3. Mapped Types

```typescript
type Readonly<T> = { readonly [P in keyof T]: T[P] };
type Partial<T> = { [P in keyof T]?: T[P] };

// Key remapping
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

// Filter properties by type
type PickByType<T, U> = {
  [K in keyof T as T[K] extends U ? K : never]: T[K];
};
```

### 4. Template Literal Types

```typescript
type EventName = "click" | "focus" | "blur";
type EventHandler = `on${Capitalize<EventName>}`;
// "onClick" | "onFocus" | "onBlur"

type Path<T> = T extends object
  ? {
      [K in keyof T]: K extends string ? `${K}` | `${K}.${Path<T[K]>}` : never;
    }[keyof T]
  : never;
```

### 5. Utility Types

```typescript
type PartialUser = Partial<User>; // All optional
type RequiredUser = Required<PartialUser>; // All required
type ReadonlyUser = Readonly<User>; // All readonly
type UserName = Pick<User, "name" | "email">;
type UserWithoutPassword = Omit<User, "password">;
type T1 = Exclude<"a" | "b" | "c", "a">; // "b" | "c"
type T2 = Extract<"a" | "b" | "c", "a" | "b">; // "a" | "b"
type T3 = NonNullable<string | null | undefined>; // string
```

## Advanced Patterns

### Type-Safe Event Emitter

```typescript
type EventMap = {
  "user:created": { id: string; name: string };
  "user:updated": { id: string };
};

class TypedEventEmitter<T extends Record<string, any>> {
  private listeners: { [K in keyof T]?: Array<(data: T[K]) => void> } = {};

  on<K extends keyof T>(event: K, callback: (data: T[K]) => void): void {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event]!.push(callback);
  }

  emit<K extends keyof T>(event: K, data: T[K]): void {
    this.listeners[event]?.forEach((cb) => cb(data));
  }
}
```

### Discriminated Unions

```typescript
type Success<T> = { status: "success"; data: T };
type Failure = { status: "error"; error: string };
type Loading = { status: "loading" };
type AsyncState<T> = Success<T> | Failure | Loading;

function handleState<T>(state: AsyncState<T>): void {
  switch (state.status) {
    case "success":
      console.log(state.data);
      break;
    case "error":
      console.log(state.error);
      break;
    case "loading":
      console.log("Loading...");
      break;
  }
}
```

### Deep Readonly/Partial

```typescript
type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object
    ? T[P] extends Function
      ? T[P]
      : DeepReadonly<T[P]>
    : T[P];
};

type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object
    ? T[P] extends Array<infer U>
      ? Array<DeepPartial<U>>
      : DeepPartial<T[P]>
    : T[P];
};
```

### Type Guards & Assertion Functions

```typescript
function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isArrayOf<T>(
  value: unknown,
  guard: (item: unknown) => item is T,
): value is T[] {
  return Array.isArray(value) && value.every(guard);
}

function assertIsString(value: unknown): asserts value is string {
  if (typeof value !== "string") throw new Error("Not a string");
}
```

### Infer Keyword

```typescript
type ElementType<T> = T extends (infer U)[] ? U : never;
type PromiseType<T> = T extends Promise<infer U> ? U : never;
type Parameters<T> = T extends (...args: infer P) => any ? P : never;
```

## Best Practices

1. **Use `unknown` over `any`** — enforce type checking
2. **Prefer `interface` for object shapes** — better error messages
3. **Use `type` for unions and complex types** — more flexible
4. **Leverage type inference** — let TypeScript infer when possible
5. **Use strict mode** — enable all strict compiler options
6. **Avoid type assertions** — use type guards instead
7. **Test your types** — use `AssertEqual` helpers for type tests

## Common Pitfalls

1. **Over-using `any`** — defeats TypeScript's purpose
2. **Ignoring strict null checks** — runtime errors
3. **Too complex types** — slows compilation
4. **Not using discriminated unions** — misses type narrowing
5. **Circular type references** — compiler errors
