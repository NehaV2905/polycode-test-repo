// main.rs — Rust orchestration, error propagation, and Analyzer
// Showcases: mod system, Result chaining, ? operator, struct with impl, custom error types
mod task;
mod manager;

use std::collections::HashMap;
use std::time::SystemTime;

use task::{Priority, Status, Tag, Task, TaskError};
use manager::{Manage, TaskManager};

// ── Analyzer ──────────────────────────────────────────────────────────────────

#[derive(Debug)]
pub struct MetricSnapshot {
    pub total: usize,
    pub by_status: HashMap<String, usize>,
    pub by_priority: HashMap<String, usize>,
    pub completion_rate: f64,
    pub overdue_count: usize,
    pub avg_age_days: f64,
    pub priority_debt: f64,
}

impl MetricSnapshot {
    pub fn summary(&self) -> String {
        format!(
            "total={}, done={:.0}%, overdue={}, debt={:.2}",
            self.total,
            self.completion_rate * 100.0,
            self.overdue_count,
            self.priority_debt,
        )
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AnalysisError {
    #[error("no tasks to analyse")]
    EmptyCollection,
    #[error("task error: {0}")]
    TaskError(#[from] TaskError),
}

pub struct Analyzer<'a> {
    manager: &'a TaskManager,
}

impl<'a> Analyzer<'a> {
    pub fn new(manager: &'a TaskManager) -> Self {
        Analyzer { manager }
    }

    pub fn snapshot(&self) -> Result<MetricSnapshot, AnalysisError> {
        if self.manager.is_empty() {
            return Err(AnalysisError::EmptyCollection);
        }

        let tasks = self.manager.all();
        let n = tasks.len();

        let mut by_status: HashMap<String, usize> = HashMap::new();
        let mut by_priority: HashMap<String, usize> = HashMap::new();
        let mut total_age = 0u64;
        let mut overdue_count = 0;
        let mut done_count = 0;

        for t in &tasks {
            *by_status.entry(t.status.to_string()).or_insert(0) += 1;
            *by_priority.entry(t.priority.to_string()).or_insert(0) += 1;
            total_age += t.age_days();
            if t.is_overdue() { overdue_count += 1; }
            if t.status == Status::Done { done_count += 1; }
        }

        let debt = tasks.iter()
            .filter(|t| t.priority.is_urgent() && !t.status.is_terminal())
            .map(|t| t.priority.weight() as f64 * (1.0 + t.age_days() as f64).ln())
            .sum::<f64>();

        Ok(MetricSnapshot {
            total: n,
            by_status,
            by_priority,
            completion_rate: done_count as f64 / n as f64,
            overdue_count,
            avg_age_days: total_age as f64 / n as f64,
            priority_debt: (debt * 100.0).round() / 100.0,
        })
    }

    pub fn rank(&self, top_n: Option<usize>) -> Vec<&Task> {
        self.manager.rank_by_score(top_n)
    }

    pub fn detect_patterns(&self) -> HashMap<&'static str, Vec<&Task>> {
        let mut patterns: HashMap<&'static str, Vec<&Task>> = HashMap::new();

        patterns.insert("stale_todo", self.manager.filter(|t| {
            t.status == Status::Todo && t.age_days() > 30
        }));
        patterns.insert("high_priority_blocked", self.manager.filter(|t| {
            t.status == Status::Blocked && t.priority.is_urgent()
        }));
        patterns.insert("overdue_critical", self.manager.filter(|t| {
            t.is_overdue() && t.priority == Priority::Critical
        }));

        patterns
    }

    pub fn health_summary(&self) -> String {
        match self.snapshot() {
            Ok(snap) => {
                let mut issues = Vec::new();
                if snap.overdue_count >= 10 {
                    issues.push(format!("{} overdue tasks", snap.overdue_count));
                }
                if snap.completion_rate < 0.3 {
                    issues.push(format!("low completion ({:.0}%)", snap.completion_rate * 100.0));
                }
                if issues.is_empty() {
                    format!("✅ Healthy — {}", snap.summary())
                } else {
                    format!("⚠️ Issues: {}", issues.join(", "))
                }
            }
            Err(e) => format!("❌ Error: {}", e),
        }
    }
}

// ── Main / demo ───────────────────────────────────────────────────────────────

fn build_demo_manager() -> Result<TaskManager, TaskError> {
    let mut mgr = TaskManager::new("demo");

    let mut t1 = Task::new("Implement gRPC client", Priority::High)?;
    t1.add_tag(Tag::new("backend")?.with_color("#3b82f6"));
    t1.description = "Wire up the tonic gRPC client to Module 1".to_string();

    let t2 = Task::new("Write integration tests", Priority::Medium)?;
    let t3 = Task::new("Update README", Priority::Low)?;

    let mut t4 = Task::new("Critical: fix memory leak in IR builder", Priority::Critical)?;
    t4.add_tag(Tag::new("bug")?);

    mgr.add(t1);
    mgr.add(t2);
    mgr.add(t3);
    mgr.add(t4);

    Ok(mgr)
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mgr = build_demo_manager()?;
    let analyzer = Analyzer::new(&mgr);

    println!("{}", mgr);
    println!("{}", analyzer.health_summary());

    let snap = analyzer.snapshot()?;
    println!("Snapshot: {}", snap.summary());

    let top3 = analyzer.rank(Some(3));
    println!("Top 3 by urgency:");
    for (i, task) in top3.iter().enumerate() {
        println!("  {}. {} (score={:.1})", i + 1, task.title, task.score());
    }

    let patterns = analyzer.detect_patterns();
    for (name, tasks) in &patterns {
        println!("Pattern '{}': {} tasks", name, tasks.len());
    }

    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Fatal error: {}", e);
        std::process::exit(1);
    }
}

// ── Dead code ─────────────────────────────────────────────────────────────────

/// Old main — kept for reference. Never called.
#[allow(dead_code)]
fn legacy_main() {
    let mgr = TaskManager::new("legacy");
    println!("tasks: {}", mgr.len());
}
