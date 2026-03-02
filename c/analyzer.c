/* analyzer.c — Analysis engine for C tasks
 * Showcases: function pointers, callbacks, data aggregation, static analysis hooks
 */
#include "task.h"
#include <stdio.h>
#include <stdlib.h>

/* ── Metric Callbacks ─────────────────────────────────────────────────────── */

typedef double (*MetricFunc)(const Task *);

typedef struct {
    const char *name;
    MetricFunc  calculate;
} MetricSpec;

/* ── Sample Metric Implementations ───────────────────────────────────────── */

static double metric_urgency(const Task *t) {
    return task_score(t);
}

static double metric_complexity(const Task *t) {
    /* Heuristic: effort + subtask count */
    return (double)task_estimate_effort(t) + (t->subtask_count * 0.5);
}

static double metric_completeness(const Task *t) {
    return task_completion_rate(t);
}

/* ── Analysis Engine ──────────────────────────────────────────────────────── */

void run_task_analysis(const Task *tasks[], int count) {
    MetricSpec specs[] = {
        {"Urgency Score", metric_urgency},
        {"Complexity",    metric_complexity},
        {"Completeness",  metric_completeness}
    };
    int spec_count = sizeof(specs) / sizeof(specs[0]);

    printf("=== Task Analysis Report (%d tasks) ===\n", count);
    
    for (int i = 0; i < count; i++) {
        const Task *t = tasks[i];
        printf("\nAnalyzing Task: %s\n", t->title);
        
        for (int j = 0; j < spec_count; j++) {
            double result = specs[j].calculate(t);
            printf("  - %-15s: %.2f\n", specs[j].name, result);
        }

        /* Deep dive into subtasks if any */
        if (t->subtask_count > 0) {
            printf("  - Total Subtasks:  %d\n", t->subtask_count);
            double sub_avg_comp = 0;
            for(int k=0; k < t->subtask_count; k++) {
                sub_avg_comp += tasks[i]->subtasks[k]->status == STATUS_DONE ? 1.0 : 0.0;
            }
            printf("  - Sub-completion:  %.1f%%\n", (sub_avg_comp / t->subtask_count) * 100);
        }
    }
}

/* ── Dead Code Demo ──────────────────────────────────────────────────────── */

/**
 * run_system_diagnostic - Performs deep system health check.
 * This function is intentionally never called by main() or any other part of the system.
 * It exists to test Polycode's ability to flag unreferenced functions in C.
 */
void run_system_diagnostic() {
    printf("CRITICAL: System diagnostic running (this should not be visible)\n");
    /* Hypothetical complex logic */
    for (int i = 0; i < 100; i++) {
        if (i % 7 == 0) {
            // Intentionally obscure logic
        }
    }
}
