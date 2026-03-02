/* main.c — Entry point for C task management showcase
 * Showcases: orchestration, memory management, task hierarchy, pipeline execution
 */
#include "task.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* Forward declaration from analyzer.c */
void run_task_analysis(const Task *tasks[], int count);

int main() {
    /* Initialize RNG for dummy UUID generation */
    srand((unsigned int)time(NULL));

    puts("--- Polycode C Showcase ---");

    /* 1. Create top-level tasks */
    Task *t1 = task_create("Engine Overhaul", PRIORITY_CRITICAL);
    Task *t2 = task_create("UI Design System", PRIORITY_MEDIUM);
    Task *t3 = task_create("Security Audit", PRIORITY_HIGH);

    /* 2. Build Hierarchy */
    Task *sub1 = task_create("Refactor Parser", PRIORITY_HIGH);
    Task *sub2 = task_create("Optimize Memory", PRIORITY_MEDIUM);
    
    task_add_subtask(t1, sub1);
    task_add_subtask(t1, sub2);

    /* 3. Add Metadata */
    task_add_tag(t1, "core", "#ff0000");
    task_add_tag(t1, "perf", "#0000ff");
    task_add_tag(t3, "security", "#ffff00");

    /* 4. Simulate State Transitions */
    task_transition(t1, STATUS_IN_PROGRESS);
    task_transition(sub1, STATUS_DONE);
    
    /* Set a due date (3 days from now) */
    t3->due_date = time(NULL) + (3 * 24 * 60 * 60);

    /* 5. Orchestrate Analysis Pipeline */
    const Task *analysis_queue[] = { t1, t2, t3 };
    run_task_analysis(analysis_queue, 3);

    /* 6. Verify Task Print */
    printf("\n--- Sample Task Output ---\n");
    task_print(t1);
    task_print(t3);

    /* 7. Memory Cleanup (recursive) */
    task_destroy(t1);
    task_destroy(t2);
    task_destroy(t3);

    puts("\nDemo completed successfully.");
    return 0;
}
