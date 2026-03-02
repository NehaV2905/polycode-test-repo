package taskmanager;

import java.util.*;
import java.util.function.*;
import java.util.stream.*;

/**
 * TaskManager.java — Generic task manager with Java streams and lambdas.
 * Showcases: generics, streams, lambdas, method references, Optional, Comparator chaining.
 */
public class TaskManager<T extends Task> {

    private final Map<String, T> store = new LinkedHashMap<>();
    private final String name;

    public TaskManager(String name) {
        this.name = name;
    }

    // ── CRUD ──────────────────────────────────────────────────────────────────

    public void add(T task) {
        Objects.requireNonNull(task);
        store.put(task.getId(), task);
    }

    public Optional<T> findById(String id) {
        return Optional.ofNullable(store.get(id));
    }

    public boolean remove(String id) {
        return store.remove(id) != null;
    }

    public List<T> all() {
        return new ArrayList<>(store.values());
    }

    public int size() { return store.size(); }

    public boolean isEmpty() { return store.isEmpty(); }

    // ── Stream-based queries ──────────────────────────────────────────────────

    public List<T> findByStatus(Task.Status... statuses) {
        Set<Task.Status> allowed = EnumSet.copyOf(Arrays.asList(statuses));
        return store.values().stream()
            .filter(t -> allowed.contains(t.getStatus()))
            .collect(Collectors.toList());
    }

    public List<T> findByPriorityAtLeast(Task.Priority min) {
        return store.values().stream()
            .filter(t -> t.getPriority().getWeight() >= min.getWeight())
            .sorted(Comparator.comparingInt((T t) -> t.getPriority().getWeight()).reversed())
            .collect(Collectors.toList());
    }

    public List<T> findOverdue() {
        return store.values().stream()
            .filter(Task::isOverdue)
            .sorted()
            .collect(Collectors.toList());
    }

    public List<T> search(Predicate<T> predicate) {
        return store.values().stream()
            .filter(predicate)
            .collect(Collectors.toList());
    }

    public Map<Task.Status, List<T>> groupByStatus() {
        return store.values().stream()
            .collect(Collectors.groupingBy(Task::getStatus));
    }

    public Map<Task.Priority, Long> countByPriority() {
        return store.values().stream()
            .collect(Collectors.groupingBy(Task::getPriority, Collectors.counting()));
    }

    /** Return top-N tasks sorted by a provided scoring function. */
    public List<T> topN(int n, ToDoubleFunction<T> scorer) {
        return store.values().stream()
            .sorted(Comparator.comparingDouble(scorer).reversed())
            .limit(n)
            .collect(Collectors.toList());
    }

    // ── Bulk operations ───────────────────────────────────────────────────────

    public int bulkTransition(Predicate<T> filter, Task.Status newStatus) {
        List<T> targets = search(filter);
        targets.forEach(t -> {
            try { t.transition(newStatus); }
            catch (IllegalStateException ignored) {}
        });
        return targets.size();
    }

    public void forEach(Consumer<T> action) {
        store.values().forEach(action);
    }

    public void removeIf(Predicate<T> condition) {
        store.values().removeIf(condition);
    }

    // ── Statistics ────────────────────────────────────────────────────────────

    public OptionalDouble averageEffort() {
        return store.values().stream()
            .mapToInt(Task::estimateEffort)
            .average();
    }

    public OptionalDouble averageCompletionRate() {
        return store.values().stream()
            .mapToDouble(Task::completionRate)
            .average();
    }

    public long countDone() {
        return store.values().stream()
            .filter(t -> t.getStatus() == Task.Status.DONE)
            .count();
    }

    public double overallCompletionRate() {
        if (store.isEmpty()) return 0.0;
        return (double) countDone() / store.size();
    }

    // ── Functional pipeline factory methods ───────────────────────────────────

    public static <T extends Task> Predicate<T> hasTag(String tag) {
        return t -> t.getTags().contains(tag);
    }

    public static <T extends Task> Predicate<T> isUrgent() {
        return t -> t.getPriority().isUrgentOrAbove();
    }

    public static <T extends Task> Comparator<T> byUrgency() {
        return Comparator.comparingInt((T t) -> t.getPriority().getWeight()).reversed()
            .thenComparingLong(Task::getAgeDays).reversed();
    }

    // ── toString ──────────────────────────────────────────────────────────────

    @Override
    public String toString() {
        return String.format("TaskManager{name='%s', size=%d, completion=%.1f%%}",
            name, size(), overallCompletionRate() * 100);
    }

    // ── Dead code ─────────────────────────────────────────────────────────────

    /** @deprecated Use {@link #findByStatus} with varargs. Never called. */
    @Deprecated
    private List<T> legacyFindActive() {
        return store.values().stream()
            .filter(t -> !t.getStatus().isTerminal())
            .collect(Collectors.toList());
    }
}
