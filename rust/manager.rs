// manager.rs — Generic task manager with iterators, closures, and trait objects
// Showcases: generics, trait bounds, iterators, closures, Box<dyn Trait>, HashMap
use std::collections::HashMap;

use crate::task::{Priority, Scorable, Status, Task, TaskError};

// ── Manager trait ─────────────────────────────────────────────────────────────

pub trait Manage<T> {
    fn add(&mut self, item: T);
    fn get(&self, id: &str) -> Option<&T>;
    fn remove(&mut self, id: &str) -> bool;
    fn all(&self) -> Vec<&T>;
    fn len(&self) -> usize;
    fn is_empty(&self) -> bool { self.len() == 0 }
}

// ── TaskManager ───────────────────────────────────────────────────────────────

pub struct TaskManager {
    name: String,
    store: HashMap<String, Task>,
}

impl TaskManager {
    pub fn new(name: impl Into<String>) -> Self {
        TaskManager {
            name: name.into(),
            store: HashMap::new(),
        }
    }

    // ── Queries using iterators + closures ────────────────────────────────

    pub fn filter<'a, F>(&'a self, pred: F) -> Vec<&'a Task>
    where
        F: Fn(&Task) -> bool,
    {
        self.store.values().filter(|t| pred(t)).collect()
    }

    pub fn find_by_status(&self, status: &Status) -> Vec<&Task> {
        self.filter(|t| &t.status == status)
    }

    pub fn find_overdue(&self) -> Vec<&Task> {
        self.filter(|t| t.is_overdue())
    }

    pub fn find_by_priority_at_least(&self, min: Priority) -> Vec<&Task> {
        self.filter(|t| t.priority >= min)
    }

    pub fn rank_by_score(&self, top_n: Option<usize>) -> Vec<&Task> {
        let mut tasks: Vec<&Task> = self.store.values().collect();
        tasks.sort_by(|a, b| b.score().partial_cmp(&a.score()).unwrap_or(std::cmp::Ordering::Equal));
        match top_n {
            Some(n) => tasks.into_iter().take(n).collect(),
            None    => tasks,
        }
    }

    pub fn group_by_status(&self) -> HashMap<String, Vec<&Task>> {
        let mut groups: HashMap<String, Vec<&Task>> = HashMap::new();
        for task in self.store.values() {
            groups.entry(task.status.to_string()).or_default().push(task);
        }
        groups
    }

    pub fn count_by_priority(&self) -> HashMap<String, usize> {
        let mut counts: HashMap<String, usize> = HashMap::new();
        for task in self.store.values() {
            *counts.entry(task.priority.to_string()).or_insert(0) += 1;
        }
        counts
    }

    // ── Aggregate stats ───────────────────────────────────────────────────

    pub fn completion_rate(&self) -> f64 {
        if self.store.is_empty() { return 0.0; }
        let done = self.store.values().filter(|t| t.status == Status::Done).count();
        done as f64 / self.store.len() as f64
    }

    pub fn average_effort(&self) -> f64 {
        if self.store.is_empty() { return 0.0; }
        let total: u32 = self.store.values().map(|t| t.estimate_effort()).sum();
        total as f64 / self.store.len() as f64
    }

    pub fn total_score(&self) -> f64 {
        self.store.values().map(|t| t.score()).sum()
    }

    // ── Bulk mutations ────────────────────────────────────────────────────

    pub fn bulk_transition<F>(&mut self, pred: F, new_status: Status) -> usize
    where
        F: Fn(&Task) -> bool,
    {
        let ids: Vec<String> = self.store
            .values()
            .filter(|t| pred(t))
            .map(|t| t.id.clone())
            .collect();

        let mut count = 0;
        for id in ids {
            if let Some(task) = self.store.get_mut(&id) {
                if task.transition(new_status.clone()).is_ok() {
                    count += 1;
                }
            }
        }
        count
    }

    pub fn remove_if<F>(&mut self, pred: F) -> usize
    where
        F: Fn(&Task) -> bool,
    {
        let before = self.store.len();
        self.store.retain(|_, t| !pred(t));
        before - self.store.len()
    }

    // ── Iterator adapters ─────────────────────────────────────────────────

    pub fn iter(&self) -> impl Iterator<Item = &Task> {
        self.store.values()
    }

    pub fn iter_active(&self) -> impl Iterator<Item = &Task> {
        self.store.values().filter(|t| !t.status.is_terminal())
    }

    /// Apply a transformation and collect into a Vec.
    pub fn map_collect<B, F>(&self, f: F) -> Vec<B>
    where
        F: Fn(&Task) -> B,
    {
        self.store.values().map(f).collect()
    }

    /// Fold over all tasks.
    pub fn fold<B, F>(&self, init: B, f: F) -> B
    where
        F: Fn(B, &Task) -> B,
    {
        self.store.values().fold(init, f)
    }
}

impl Manage<Task> for TaskManager {
    fn add(&mut self, item: Task) {
        self.store.insert(item.id.clone(), item);
    }

    fn get(&self, id: &str) -> Option<&Task> {
        self.store.get(id)
    }

    fn remove(&mut self, id: &str) -> bool {
        self.store.remove(id).is_some()
    }

    fn all(&self) -> Vec<&Task> {
        self.store.values().collect()
    }

    fn len(&self) -> usize {
        self.store.len()
    }
}

impl std::fmt::Display for TaskManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "TaskManager {{ name={:?}, size={}, completion={:.0}% }}",
            self.name, self.store.len(), self.completion_rate() * 100.0)
    }
}

// ── Dead code ─────────────────────────────────────────────────────────────────

/// Old linear search — replaced by HashMap lookup. Never called.
#[allow(dead_code)]
fn linear_search<'a>(store: &'a HashMap<String, Task>, id: &str) -> Option<&'a Task> {
    store.values().find(|t| t.id == id)
}
