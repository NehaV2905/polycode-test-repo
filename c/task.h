/* task.h — Task domain model header (C99)
 * Showcases: structs, enums, function prototypes, typedefs, macros
 */
#ifndef TASK_H
#define TASK_H

#include <stddef.h>
#include <time.h>

/* ── Constants ─────────────────────────────────────────────────────────────── */

#define TASK_ID_LEN     37   /* UUID string length including null terminator */
#define TASK_TITLE_MAX  256
#define TASK_DESC_MAX   1024
#define MAX_TAGS        16
#define MAX_SUBTASKS    64
#define TAG_NAME_MAX    64

/* ── Enumerations ───────────────────────────────────────────────────────────── */

typedef enum {
    PRIORITY_LOW      = 1,
    PRIORITY_MEDIUM   = 2,
    PRIORITY_HIGH     = 4,
    PRIORITY_CRITICAL = 8
} Priority;

typedef enum {
    STATUS_TODO        = 0,
    STATUS_IN_PROGRESS = 1,
    STATUS_BLOCKED     = 2,
    STATUS_DONE        = 3,
    STATUS_CANCELLED   = 4
} Status;

/* ── Structs ────────────────────────────────────────────────────────────────── */

typedef struct {
    char name[TAG_NAME_MAX];
    char color[16];   /* hex color: #rrggbb */
} Tag;

typedef struct Task {
    char         id[TASK_ID_LEN];
    char         title[TASK_TITLE_MAX];
    char         description[TASK_DESC_MAX];
    Priority     priority;
    Status       status;
    Tag          tags[MAX_TAGS];
    int          tag_count;
    struct Task *subtasks[MAX_SUBTASKS];
    int          subtask_count;
    time_t       created_at;
    time_t       updated_at;
    time_t       due_date;          /* 0 = no due date */
} Task;

/* ── Function prototypes ────────────────────────────────────────────────────── */

/* Lifecycle */
Task  *task_create(const char *title, Priority priority);
void   task_destroy(Task *task);
Task  *task_copy(const Task *src);

/* Properties */
int    task_is_overdue(const Task *task);
int    task_age_days(const Task *task);
double task_completion_rate(const Task *task);
int    task_estimate_effort(const Task *task);
double task_score(const Task *task);

/* Mutation */
int    task_transition(Task *task, Status new_status);
int    task_add_subtask(Task *task, Task *subtask);
int    task_add_tag(Task *task, const char *name, const char *color);
int    task_remove_tag(Task *task, const char *name);

/* Utilities */
int    task_is_terminal(Status status);
int    priority_weight(Priority p);
const char *priority_to_str(Priority p);
const char *status_to_str(Status s);
void   task_print(const Task *task);

/* ── Macro helpers ──────────────────────────────────────────────────────────── */

#define PRIORITY_IS_URGENT(p)  ((int)(p) >= (int)PRIORITY_HIGH)
#define TASK_HAS_DUE_DATE(t)   ((t)->due_date != 0)

#endif /* TASK_H */
