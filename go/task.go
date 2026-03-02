// task.go — Task domain model
// Showcases: structs, methods, interfaces, iota enums, embedding, stringer, pointer receivers
package taskmanager

import (
	"errors"
	"fmt"
	"math"
	"time"

	"github.com/google/uuid"
)

// ── Priority ──────────────────────────────────────────────────────────────────

type Priority int

const (
	PriorityLow Priority = iota + 1
	PriorityMedium
	PriorityHigh
	PriorityCritical
)

func (p Priority) Weight() int {
	weights := map[Priority]int{
		PriorityLow:      1,
		PriorityMedium:   2,
		PriorityHigh:     4,
		PriorityCritical: 8,
	}
	if w, ok := weights[p]; ok {
		return w
	}
	return 0
}

func (p Priority) String() string {
	names := map[Priority]string{
		PriorityLow:      "LOW",
		PriorityMedium:   "MEDIUM",
		PriorityHigh:     "HIGH",
		PriorityCritical: "CRITICAL",
	}
	if s, ok := names[p]; ok {
		return s
	}
	return "UNKNOWN"
}

func (p Priority) IsUrgent() bool {
	return p >= PriorityHigh
}

// ── Status ────────────────────────────────────────────────────────────────────

type Status string

const (
	StatusTodo       Status = "todo"
	StatusInProgress Status = "in_progress"
	StatusBlocked    Status = "blocked"
	StatusDone       Status = "done"
	StatusCancelled  Status = "cancelled"
)

func (s Status) IsTerminal() bool {
	return s == StatusDone || s == StatusCancelled
}

func ActiveStatuses() []Status {
	return []Status{StatusTodo, StatusInProgress, StatusBlocked}
}

// ── Interfaces ────────────────────────────────────────────────────────────────

// Scorable can compute a numeric urgency score.
type Scorable interface {
	Score() float64
}

// Filterable checks a predicate against itself.
type Filterable interface {
	Matches(pred func(*Task) bool) bool
}

// ── Tag ───────────────────────────────────────────────────────────────────────

type Tag struct {
	Name  string
	Color string
}

func NewTag(name, color string) (Tag, error) {
	if name == "" {
		return Tag{}, errors.New("tag name cannot be empty")
	}
	return Tag{Name: name, Color: color}, nil
}

func (t Tag) String() string { return "#" + t.Name }

// ── Task ──────────────────────────────────────────────────────────────────────

type Task struct {
	ID          string
	Title       string
	Description string
	Priority    Priority
	Status      Status
	Tags        []Tag
	DueDate     *time.Time
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Subtasks    []*Task
}

// NewTask constructs a Task with defaults.
func NewTask(title string, priority Priority) (*Task, error) {
	if title == "" {
		return nil, errors.New("title must not be empty")
	}
	now := time.Now().UTC()
	return &Task{
		ID:        uuid.New().String(),
		Title:     title,
		Priority:  priority,
		Status:    StatusTodo,
		CreatedAt: now,
		UpdatedAt: now,
		Subtasks:  make([]*Task, 0),
		Tags:      make([]Tag, 0),
	}, nil
}

// ── Computed fields ───────────────────────────────────────────────────────────

func (t *Task) IsOverdue() bool {
	if t.DueDate == nil || t.Status.IsTerminal() {
		return false
	}
	return time.Now().UTC().After(*t.DueDate)
}

func (t *Task) AgeDays() int {
	return int(time.Since(t.CreatedAt).Hours() / 24)
}

func (t *Task) CompletionRate() float64 {
	if len(t.Subtasks) == 0 {
		if t.Status == StatusDone {
			return 1.0
		}
		return 0.0
	}
	done := 0
	for _, s := range t.Subtasks {
		if s.Status == StatusDone {
			done++
		}
	}
	return float64(done) / float64(len(t.Subtasks))
}

func (t *Task) EstimateEffort() int {
	base := t.Priority.Weight() * 2
	subPenalty := len(t.Subtasks) / 3
	overduePenalty := 0
	if t.IsOverdue() {
		overduePenalty = 1
	}
	return base + subPenalty + overduePenalty
}

// Score implements Scorable.
func (t *Task) Score() float64 {
	base := float64(t.Priority.Weight()) * 10.0
	age := math.Log1p(float64(t.AgeDays())) * 2.0
	overdue := 0.0
	if t.IsOverdue() {
		overdue = 20.0
	}
	effort := float64(t.EstimateEffort()) * 0.5
	return base + age + overdue - effort
}

// Matches implements Filterable.
func (t *Task) Matches(pred func(*Task) bool) bool {
	return pred(t)
}

// ── Mutation ──────────────────────────────────────────────────────────────────

var ErrTerminalTransition = errors.New("cannot transition from a terminal status")

func (t *Task) Transition(newStatus Status) error {
	if t.Status.IsTerminal() {
		return fmt.Errorf("%w: current=%s", ErrTerminalTransition, t.Status)
	}
	t.Status = newStatus
	t.UpdatedAt = time.Now().UTC()
	return nil
}

func (t *Task) AddSubtask(sub *Task) {
	t.Subtasks = append(t.Subtasks, sub)
	t.UpdatedAt = time.Now().UTC()
}

func (t *Task) AddTag(tag Tag) {
	for _, existing := range t.Tags {
		if existing.Name == tag.Name {
			return
		}
	}
	t.Tags = append(t.Tags, tag)
}

func (t *Task) RemoveTag(name string) {
	filtered := t.Tags[:0]
	for _, tag := range t.Tags {
		if tag.Name != name {
			filtered = append(filtered, tag)
		}
	}
	t.Tags = filtered
}

// ── Stringer ──────────────────────────────────────────────────────────────────

func (t *Task) String() string {
	return fmt.Sprintf("Task{id=%s, title=%q, status=%s, priority=%s}",
		t.ID[:8], t.Title, t.Status, t.Priority)
}

// ── Dead code ─────────────────────────────────────────────────────────────────

// legacyScoreV1 was the original scoring algorithm. Never called.
func legacyScoreV1(t *Task) float64 {
	return float64(t.Priority.Weight()) * 5.0
}
