/* task.c — Implementation of Task domain model (C99)
 * Showcases: memory management, string manipulation, time handling, pointer arithmetic
 */
#include "task.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* Helper to generate a dummy UUID-like string since standard C has no UUID lib */
static void generate_uuid(char *buf) {
    const char *chars = "0123456789abcdef";
    for (int i = 0; i < 36; i++) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            buf[i] = '-';
        } else {
            buf[i] = chars[rand() % 16];
        }
    }
    buf[36] = '\0';
}

/* ── Lifecycle ────────────────────────────────────────────────────────────── */

Task *task_create(const char *title, Priority priority) {
    Task *task = (Task *)malloc(sizeof(Task));
    if (!task) return NULL;

    memset(task, 0, sizeof(Task));
    generate_uuid(task->id);
    strncpy(task->title, title ? title : "Untitled Task", TASK_TITLE_MAX - 1);
    task->priority = priority;
    task->status = STATUS_TODO;
    task->created_at = time(NULL);
    task->updated_at = task->created_at;
    task->tag_count = 0;
    task->subtask_count = 0;
    task->due_date = 0;

    return task;
}

void task_destroy(Task *task) {
    if (!task) return;
    /* Recursively destroy subtasks */
    for (int i = 0; i < task->subtask_count; i++) {
        task_destroy(task->subtasks[i]);
    }
    free(task);
}

/* ── Properties ───────────────────────────────────────────────────────────── */

int task_is_overdue(const Task *task) {
    if (!task || task->due_date == 0 || task_is_terminal(task->status)) {
        return 0;
    }
    return time(NULL) > task->due_date;
}

int task_age_days(const Task *task) {
    if (!task) return 0;
    double seconds = difftime(time(NULL), task->created_at);
    return (int)(seconds / (60 * 60 * 24));
}

double task_completion_rate(const Task *task) {
    if (!task) return 0.0;
    if (task->subtask_count == 0) {
        return (task->status == STATUS_DONE) ? 1.0 : 0.0;
    }
    int done = 0;
    for (int i = 0; i < task->subtask_count; i++) {
        if (task->subtasks[i]->status == STATUS_DONE) {
            done++;
        }
    }
    return (double)done / task->subtask_count;
}

int task_estimate_effort(const Task *task) {
    if (!task) return 0;
    int base = priority_weight(task->priority) * 2;
    int sub_penalty = task->subtask_count / 3;
    int overdue_penalty = task_is_overdue(task) ? 1 : 0;
    return base + sub_penalty + overdue_penalty;
}

double task_score(const Task *task) {
    if (!task) return 0.0;
    double base = (double)priority_weight(task->priority) * 10.0;
    double age = log1p((double)task_age_days(task)) * 2.0;
    double overdue = task_is_overdue(task) ? 20.0 : 0.0;
    double effort = (double)task_estimate_effort(task) * 0.5;
    return base + age + overdue - effort;
}

/* ── Mutation ─────────────────────────────────────────────────────────────── */

int task_transition(Task *task, Status new_status) {
    if (!task || task_is_terminal(task->status)) {
        return -1;
    }
    task->status = new_status;
    task->updated_at = time(NULL);
    return 0;
}

int task_add_subtask(Task *task, Task *subtask) {
    if (!task || !subtask || task->subtask_count >= MAX_SUBTASKS) {
        return -1;
    }
    task->subtasks[task->subtask_count++] = subtask;
    task->updated_at = time(NULL);
    return 0;
}

int task_add_tag(Task *task, const char *name, const char *color) {
    if (!task || !name || task->tag_count >= MAX_TAGS) {
        return -1;
    }
    /* Check for duplicate */
    for (int i = 0; i < task->tag_count; i++) {
        if (strcmp(task->tags[i].name, name) == 0) return 0;
    }
    strncpy(task->tags[task->tag_count].name, name, TAG_NAME_MAX - 1);
    strncpy(task->tags[task->tag_count].color, color ? color : "#888888", 15);
    task->tag_count++;
    return 0;
}

/* ── Utilities ────────────────────────────────────────────────────────────── */

int task_is_terminal(Status status) {
    return (status == STATUS_DONE || status == STATUS_CANCELLED);
}

int priority_weight(Priority p) {
    switch (p) {
        case PRIORITY_LOW: return 1;
        case PRIORITY_MEDIUM: return 2;
        case PRIORITY_HIGH: return 4;
        case PRIORITY_CRITICAL: return 8;
        default: return 0;
    }
}

const char *priority_to_str(Priority p) {
    switch (p) {
        case PRIORITY_LOW: return "LOW";
        case PRIORITY_MEDIUM: return "MEDIUM";
        case PRIORITY_HIGH: return "HIGH";
        case PRIORITY_CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

const char *status_to_str(Status s) {
    switch (s) {
        case STATUS_TODO: return "TODO";
        case STATUS_IN_PROGRESS: return "IN_PROGRESS";
        case STATUS_BLOCKED: return "BLOCKED";
        case STATUS_DONE: return "DONE";
        case STATUS_CANCELLED: return "CANCELLED";
        default: return "UNKNOWN";
    }
}

void task_print(const Task *task) {
    if (!task) return;
    printf("Task{id=%.8s, title='%s', status=%s, priority=%s}\n",
           task->id, task->title, status_to_str(task->status), 
           priority_to_str(task->priority));
}
