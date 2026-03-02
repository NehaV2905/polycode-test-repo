// task.rs — Task domain model for Rust
// Showcases: structs, enums, traits, derive macros, Option, Result, impl blocks, From/Into
use std::fmt;
use std::time::{Duration, SystemTime};

use uuid::Uuid;

// ── Priority ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Priority {
    Low = 1,
    Medium = 2,
    High = 4,
    Critical = 8,
}

impl Priority {
    pub fn weight(self) -> u32 {
        self as u32
    }

    pub fn is_urgent(self) -> bool {
        self >= Priority::High
    }

    pub fn all() -> &'static [Priority] {
        &[Priority::Low, Priority::Medium, Priority::High, Priority::Critical]
    }
}

impl fmt::Display for Priority {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            Priority::Low      => "LOW",
            Priority::Medium   => "MEDIUM",
            Priority::High     => "HIGH",
            Priority::Critical => "CRITICAL",
        };
        write!(f, "{}", s)
    }
}

impl From<u32> for Priority {
    fn from(v: u32) -> Self {
        match v {
            1 => Priority::Low,
            2 => Priority::Medium,
            4 => Priority::High,
            8 => Priority::Critical,
            _ => Priority::Medium,
        }
    }
}

// ── Status ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Status {
    Todo,
    InProgress,
    Blocked,
    Done,
    Cancelled,
}

impl Status {
    pub fn is_terminal(&self) -> bool {
        matches!(self, Status::Done | Status::Cancelled)
    }

    pub fn active_states() -> Vec<Status> {
        vec![Status::Todo, Status::InProgress, Status::Blocked]
    }
}

impl fmt::Display for Status {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            Status::Todo       => "todo",
            Status::InProgress => "in_progress",
            Status::Blocked    => "blocked",
            Status::Done       => "done",
            Status::Cancelled  => "cancelled",
        };
        write!(f, "{}", s)
    }
}

// ── Tag ───────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Tag {
    pub name: String,
    pub color: String,
}

impl Tag {
    pub fn new(name: impl Into<String>) -> Result<Self, &'static str> {
        let name = name.into();
        if name.trim().is_empty() {
            return Err("tag name cannot be empty");
        }
        Ok(Tag { name, color: "#888888".to_string() })
    }

    pub fn with_color(mut self, color: impl Into<String>) -> Self {
        self.color = color.into();
        self
    }
}

impl fmt::Display for Tag {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "#{}", self.name)
    }
}

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, thiserror::Error)]
pub enum TaskError {
    #[error("title must not be empty")]
    EmptyTitle,

    #[error("cannot transition from terminal status {0}")]
    TerminalTransition(Status),

    #[error("tag error: {0}")]
    TagError(&'static str),
}

// ── Task ──────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub title: String,
    pub description: String,
    pub priority: Priority,
    pub status: Status,
    pub tags: Vec<Tag>,
    pub due_date: Option<SystemTime>,
    pub created_at: SystemTime,
    pub updated_at: SystemTime,
    pub subtasks: Vec<Task>,
}

impl Task {
    pub fn new(title: impl Into<String>, priority: Priority) -> Result<Self, TaskError> {
        let title = title.into();
        if title.trim().is_empty() {
            return Err(TaskError::EmptyTitle);
        }
        let now = SystemTime::now();
        Ok(Task {
            id: Uuid::new_v4().to_string(),
            title: title.trim().to_string(),
            description: String::new(),
            priority,
            status: Status::Todo,
            tags: Vec::new(),
            due_date: None,
            created_at: now,
            updated_at: now,
            subtasks: Vec::new(),
        })
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }

    pub fn with_due_date(mut self, due: SystemTime) -> Self {
        self.due_date = Some(due);
        self
    }

    // ── Computed properties ───────────────────────────────────────────────

    pub fn is_overdue(&self) -> bool {
        match &self.due_date {
            Some(due) => !self.status.is_terminal() && SystemTime::now() > *due,
            None => false,
        }
    }

    pub fn age_days(&self) -> u64 {
        SystemTime::now()
            .duration_since(self.created_at)
            .unwrap_or(Duration::ZERO)
            .as_secs() / 86_400
    }

    pub fn completion_rate(&self) -> f64 {
        if self.subtasks.is_empty() {
            return if self.status == Status::Done { 1.0 } else { 0.0 };
        }
        let done = self.subtasks.iter().filter(|t| t.status == Status::Done).count();
        done as f64 / self.subtasks.len() as f64
    }

    pub fn estimate_effort(&self) -> u32 {
        let base = self.priority.weight() * 2;
        let sub_penalty = (self.subtasks.len() / 3) as u32;
        let overdue_penalty = if self.is_overdue() { 1 } else { 0 };
        base + sub_penalty + overdue_penalty
    }

    pub fn score(&self) -> f64 {
        let base = self.priority.weight() as f64 * 10.0;
        let age = (1.0 + self.age_days() as f64).ln() * 2.0;
        let overdue = if self.is_overdue() { 20.0 } else { 0.0 };
        let effort = self.estimate_effort() as f64 * 0.5;
        base + age + overdue - effort
    }

    // ── Mutation ──────────────────────────────────────────────────────────

    pub fn transition(&mut self, new_status: Status) -> Result<(), TaskError> {
        if self.status.is_terminal() {
            return Err(TaskError::TerminalTransition(self.status.clone()));
        }
        self.status = new_status;
        self.updated_at = SystemTime::now();
        Ok(())
    }

    pub fn add_subtask(&mut self, subtask: Task) {
        self.subtasks.push(subtask);
        self.updated_at = SystemTime::now();
    }

    pub fn add_tag(&mut self, tag: Tag) {
        if !self.tags.iter().any(|t| t.name == tag.name) {
            self.tags.push(tag);
        }
    }

    pub fn remove_tag(&mut self, name: &str) {
        self.tags.retain(|t| t.name != name);
    }
}

impl fmt::Display for Task {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Task {{ id={}, title={:?}, status={}, priority={} }}",
            &self.id[..8], self.title, self.status, self.priority)
    }
}

impl PartialEq for Task {
    fn eq(&self, other: &Self) -> bool { self.id == other.id }
}

// ── Traits ────────────────────────────────────────────────────────────────────

pub trait Scorable {
    fn score(&self) -> f64;
}

pub trait Describable {
    fn describe(&self) -> String;
}

impl Scorable for Task {
    fn score(&self) -> f64 { self.score() }
}

impl Describable for Task {
    fn describe(&self) -> String {
        format!("[{}] {} — {} ({})", self.priority, self.status, self.title, &self.id[..8])
    }
}

// ── Dead code ─────────────────────────────────────────────────────────────────

/// Legacy scoring — never called.
#[allow(dead_code)]
fn legacy_score_v1(task: &Task) -> f64 {
    task.priority.weight() as f64 * 5.0
}
