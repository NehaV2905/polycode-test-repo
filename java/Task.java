package taskmanager;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Task.java — Domain model for a Task.
 * Showcases: enums, interfaces, inner classes, generics, records (Java 16+), Comparable.
 */
public class Task implements Comparable<Task> {

    // ── Enums ────────────────────────────────────────────────────────────────

    public enum Priority {
        LOW(1), MEDIUM(2), HIGH(4), CRITICAL(8);

        private final int weight;

        Priority(int weight) { this.weight = weight; }

        public int getWeight() { return weight; }

        public boolean isUrgentOrAbove() { return this.weight >= HIGH.weight; }
    }

    public enum Status {
        TODO, IN_PROGRESS, BLOCKED, DONE, CANCELLED;

        public boolean isTerminal() {
            return this == DONE || this == CANCELLED;
        }

        public static List<Status> activeStates() {
            return List.of(TODO, IN_PROGRESS, BLOCKED);
        }
    }

    // ── Interfaces ────────────────────────────────────────────────────────────

    public interface Scorable {
        double score();
    }

    public interface Taggable {
        void addTag(String tag);
        void removeTag(String tag);
        Set<String> getTags();
    }

    // ── Inner record ─────────────────────────────────────────────────────────

    public record AuditEntry(String action, LocalDateTime timestamp, String actor) {}

    // ── Fields ────────────────────────────────────────────────────────────────

    private final String id;
    private String title;
    private String description;
    private Priority priority;
    private Status status;
    private LocalDateTime dueDate;
    private final LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private final Set<String> tags = new LinkedHashSet<>();
    private final List<Task> subtasks = new ArrayList<>();
    private final List<AuditEntry> auditLog = new ArrayList<>();

    // ── Constructor ───────────────────────────────────────────────────────────

    public Task(String title, Priority priority) {
        Objects.requireNonNull(title, "title must not be null");
        if (title.isBlank()) throw new IllegalArgumentException("title must not be blank");
        this.id = UUID.randomUUID().toString();
        this.title = title.strip();
        this.priority = priority;
        this.status = Status.TODO;
        this.createdAt = LocalDateTime.now();
        this.updatedAt = this.createdAt;
        audit("CREATED", "system");
    }

    public Task(String title) {
        this(title, Priority.MEDIUM);
    }

    // ── Getters ───────────────────────────────────────────────────────────────

    public String getId() { return id; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public Priority getPriority() { return priority; }
    public Status getStatus() { return status; }
    public Optional<LocalDateTime> getDueDate() { return Optional.ofNullable(dueDate); }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public List<Task> getSubtasks() { return Collections.unmodifiableList(subtasks); }
    public List<AuditEntry> getAuditLog() { return Collections.unmodifiableList(auditLog); }

    // ── Computed properties ───────────────────────────────────────────────────

    public boolean isOverdue() {
        return dueDate != null
            && LocalDateTime.now().isAfter(dueDate)
            && !status.isTerminal();
    }

    public long getAgeDays() {
        return java.time.temporal.ChronoUnit.DAYS.between(createdAt, LocalDateTime.now());
    }

    public double completionRate() {
        if (subtasks.isEmpty()) return status == Status.DONE ? 1.0 : 0.0;
        long done = subtasks.stream().filter(t -> t.status == Status.DONE).count();
        return (double) done / subtasks.size();
    }

    public int estimateEffort() {
        int base = priority.getWeight() * 2;
        int subPenalty = subtasks.size() / 3;
        int overduePenalty = isOverdue() ? 1 : 0;
        return base + subPenalty + overduePenalty;
    }

    // ── Mutation ──────────────────────────────────────────────────────────────

    public void setTitle(String title) {
        if (title == null || title.isBlank()) throw new IllegalArgumentException("blank title");
        this.title = title.strip();
        touch("actor");
    }

    public void setDescription(String description) {
        this.description = description;
        touch("actor");
    }

    public void setPriority(Priority priority) {
        this.priority = Objects.requireNonNull(priority);
        touch("actor");
    }

    public void setDueDate(LocalDateTime dueDate) {
        this.dueDate = dueDate;
        touch("actor");
    }

    public void transition(Status newStatus) {
        if (status.isTerminal()) {
            throw new IllegalStateException("Cannot transition from terminal status " + status);
        }
        this.status = newStatus;
        audit("STATUS_CHANGED:" + newStatus, "system");
        touch("system");
    }

    public void addSubtask(Task subtask) {
        subtasks.add(Objects.requireNonNull(subtask));
        touch("system");
    }

    public boolean removeSubtask(String subtaskId) {
        boolean removed = subtasks.removeIf(t -> t.id.equals(subtaskId));
        if (removed) touch("system");
        return removed;
    }

    public void addTag(String tag) {
        if (tag != null && !tag.isBlank()) tags.add(tag.trim());
    }

    public void removeTag(String tag) { tags.remove(tag); }

    public Set<String> getTags() { return Collections.unmodifiableSet(tags); }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void touch(String actor) {
        this.updatedAt = LocalDateTime.now();
        audit("UPDATED", actor);
    }

    private void audit(String action, String actor) {
        auditLog.add(new AuditEntry(action, LocalDateTime.now(), actor));
    }

    // ── Comparable ────────────────────────────────────────────────────────────

    @Override
    public int compareTo(Task other) {
        return Integer.compare(other.priority.getWeight(), this.priority.getWeight());
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Task task)) return false;
        return id.equals(task.id);
    }

    @Override
    public int hashCode() { return id.hashCode(); }

    @Override
    public String toString() {
        return String.format("Task{id='%s', title='%s', status=%s, priority=%s}",
            id.substring(0, 8), title, status, priority);
    }

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("title", title);
        m.put("status", status.name());
        m.put("priority", priority.name());
        m.put("overdue", isOverdue());
        m.put("ageDays", getAgeDays());
        m.put("completionRate", completionRate());
        m.put("tags", new ArrayList<>(tags));
        return m;
    }
}
