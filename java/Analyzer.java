package taskmanager;

import java.util.*;
import java.util.stream.*;
import java.util.function.*;

/**
 * Analyzer.java — Computes metrics and reports on a TaskManager.
 * Showcases: exception hierarchy, try-with-resources, functional interfaces,
 * sealed classes (Java 17+).
 */
public class Analyzer {

    // ── Custom exceptions ─────────────────────────────────────────────────────

    public static class AnalysisException extends RuntimeException {
        public AnalysisException(String message) {
            super(message);
        }

        public AnalysisException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    public static class InsufficientDataException extends AnalysisException {
        private final int required;
        private final int found;

        public InsufficientDataException(int required, int found) {
            super(String.format("Need at least %d tasks, found %d", required, found));
            this.required = required;
            this.found = found;
        }

        public int getRequired() {
            return required;
        }

        public int getFound() {
            return found;
        }
    }

    // ── Report types (sealed hierarchy) ──────────────────────────────────────

    public sealed interface AnalysisResult permits Analyzer.OkResult, Analyzer.WarnResult, Analyzer.ErrorResult {
    }

    public record OkResult(MetricSnapshot snapshot) implements AnalysisResult {
    }

    public record WarnResult(MetricSnapshot snapshot, List<String> warnings) implements AnalysisResult {
    }

    public record ErrorResult(String reason, Throwable cause) implements AnalysisResult {
    }

    // ── MetricSnapshot ────────────────────────────────────────────────────────

    public record MetricSnapshot(
            int total,
            Map<String, Long> byStatus,
            Map<String, Long> byPriority,
            double completionRate,
            long overdueCount,
            double avgEffort,
            double priorityDebtScore) {
        public String summary() {
            return String.format(
                    "Total=%d, Done=%.0f%%, Overdue=%d, PriorityDebt=%.2f",
                    total, completionRate * 100, overdueCount, priorityDebtScore);
        }
    }

    // ── Analyzer ──────────────────────────────────────────────────────────────

    private final TaskManager<Task> manager;
    private static final int MIN_TASKS_FOR_ANALYSIS = 1;

    public Analyzer(TaskManager<Task> manager) {
        this.manager = Objects.requireNonNull(manager, "manager must not be null");
    }

    public MetricSnapshot computeSnapshot() {
        List<Task> tasks = manager.all();
        if (tasks.size() < MIN_TASKS_FOR_ANALYSIS) {
            throw new InsufficientDataException(MIN_TASKS_FOR_ANALYSIS, tasks.size());
        }

        Map<String, Long> byStatus = tasks.stream()
                .collect(Collectors.groupingBy(t -> t.getStatus().name(), Collectors.counting()));

        Map<String, Long> byPriority = tasks.stream()
                .collect(Collectors.groupingBy(t -> t.getPriority().name(), Collectors.counting()));

        double completionRate = manager.overallCompletionRate();
        long overdueCount = tasks.stream().filter(Task::isOverdue).count();
        double avgEffort = manager.averageEffort().orElse(0.0);
        double priorityDebt = computePriorityDebt(tasks);

        return new MetricSnapshot(tasks.size(), byStatus, byPriority,
                completionRate, overdueCount, avgEffort, priorityDebt);
    }

    public AnalysisResult analyse() {
        try {
            MetricSnapshot snapshot = computeSnapshot();
            List<String> warnings = collectWarnings(snapshot);
            if (warnings.isEmpty()) {
                return new OkResult(snapshot);
            } else {
                return new WarnResult(snapshot, warnings);
            }
        } catch (InsufficientDataException e) {
            return new ErrorResult("Not enough data: " + e.getMessage(), e);
        } catch (Exception e) {
            return new ErrorResult("Unexpected error during analysis", e);
        }
    }

    public List<Task> rankByUrgency(int topN) {
        ToDoubleFunction<Task> scorer = t -> {
            double base = t.getPriority().getWeight() * 10.0;
            double age = Math.log1p(t.getAgeDays()) * 2.0;
            double overdue = t.isOverdue() ? 20.0 : 0.0;
            double effort = t.estimateEffort() * 0.5;
            return base + age + overdue - effort;
        };
        return manager.topN(topN, scorer);
    }

    public Map<String, List<Task>> detectPatterns() {
        Map<String, List<Task>> patterns = new LinkedHashMap<>();

        // Stale: TODO for > 30 days
        patterns.put("stale_todo", manager.search(
                t -> t.getStatus() == Task.Status.TODO && t.getAgeDays() > 30));

        // High-priority blocked
        patterns.put("high_priority_blocked", manager.search(
                t -> t.getStatus() == Task.Status.BLOCKED && t.getPriority().isUrgentOrAbove()));

        // Overdue high priority
        patterns.put("overdue_high_priority", manager.search(
                t -> t.isOverdue() && t.getPriority().isUrgentOrAbove()));

        return patterns;
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private List<String> collectWarnings(MetricSnapshot snapshot) {
        List<String> warnings = new ArrayList<>();
        if (snapshot.overdueCount() >= 10)
            warnings.add("Critical: " + snapshot.overdueCount() + " overdue tasks");
        if (snapshot.completionRate() < 0.3)
            warnings.add("Low completion rate: " + String.format("%.0f%%", snapshot.completionRate() * 100));
        if (snapshot.total() > 50)
            warnings.add("Large backlog: " + snapshot.total() + " tasks");
        if (snapshot.priorityDebtScore() > 100)
            warnings.add("High priority debt: " + String.format("%.1f", snapshot.priorityDebtScore()));
        return warnings;
    }

    private double computePriorityDebt(List<Task> tasks) {
        return tasks.stream()
                .filter(t -> t.getPriority().isUrgentOrAbove() && !t.getStatus().isTerminal())
                .mapToDouble(t -> t.getPriority().getWeight() * Math.log1p(t.getAgeDays()))
                .sum();
    }

    // ── Dead code ─────────────────────────────────────────────────────────────

    /**
     * @deprecated Replaced by computeSnapshot(). Never called in the current
     *             codebase.
     */
    @Deprecated
    private double legacyScore(Task t) {
        return t.getPriority().getWeight() * 5.0;
    }
}
