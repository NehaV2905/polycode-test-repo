# Polycode Testbed: Multi-Language Analysis Showcase

A comprehensive, cross-language demonstration repository for [Polycode](https://github.com/NehaV2905/polycode) — a universal code analysis platform.

---

## 📌 Project Overview
This repository serves as a technical showcase for Polycode's multi-language parsing, dependency extraction, and static analysis capabilities. It implements a consistent **Task Management & Metrics** domain across six programming languages, providing a standardized benchmark for evaluating Universal Intermediate Representation (IR) extraction.

### Core Capabilities Demonstrated
*   **IR Extraction**: Comprehensive mapping of classes, interfaces, enums, functions, and control flow.
*   **Dependency Graphing**: Extraction of cross-file and cross-module edges (e.g., `Calls`, `HasMember`, `Inherits`).
*   **Static Analysis**: Identification of unreachable code paths and deep call chain analysis.
*   **AI-Powered Insights**: Demonstration of Groq-powered code suggestion and vulnerability patching.

---

## � Repository Structure
The repository is organized by language, with each module implementing a "Task Management" system of equivalent complexity.

| Language | Path | Technical Highlights |
| :--- | :--- | :--- |
| **Python** | `/python` | Dataclasses, Async/Await, Decorators, Type Hinting |
| **Java** | `/java` | Generics, Streams API, Lambda Expressions, Interfaces |
| **Go** | `/go` | Goroutines, Channels, Interfaces, Pointer Receivers |
| **Rust** | `/rust` | Trait Implementations, Generics, Ownership Semantics |
| **Ruby** | `/ruby` | Mixins (Modules), Blocks/Lambdas, Enumerable Patterns |
| **C (C99)** | `/c` | Structs, Function Pointers, Manual Memory Management |

---

## 📊 Domain Model Consistency
Each implementation adheres to a shared domain logic to facilitate cross-language comparison:

*   **Task**: The primary entity (Class/Struct) with status, priority, and metadata.
*   **Priority**: Scalable importance levels (LOW to CRITICAL) with associated weights.
*   **Analyzer**: A metrics engine that calculates urgency scores and system completeness.
*   **Hierarchy**: Logical nesting of subtasks to test recursive dependency extraction.

---

## 🛠 Usage Instructions

### Integration with Polycode
To analyze this testbed using the Polycode infrastructure:

1.  **Initialize Parser Server**:
    Navigate to the `module1_adapter` directory in the main Polycode repo and launch the gRPC server:
    ```bash
    python src/main.py
    ```

2.  **Launch API Server**:
    Start the Rust-based orchestration layer:
    ```bash
    cargo run --bin api_server
    ```

3.  **Perform Analysis**:
    Point the Polycode UI or CLI at this directory root. The platform will automatically detect and analyze all six language modules simultaneously.

---

## � Expected Analysis Output
Pointed at this repository, Polycode is designed to generate:
*   **150+ IR Nodes**: Spanning classes, methods, fields, and control structures.
*   **High-Fidelity Call Graphs**: Capturing internal and cross-file method invocations.
*   **Dead Code Detection**: Intentionally unreferenced "legacy" functions included in all languages to verify static analysis triggers.
*   **Multi-Level Impact Analysis**: Evaluating how changes in core models propagate through language-specific abstractions.
