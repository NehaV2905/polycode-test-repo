// analyzer.go — Metrics, health, and pattern detection
// Showcases: closures, higher-order functions, error wrapping, struct embedding
package taskmanager

import (
	"errors"
	"fmt"
	"math"
)

// ── Errors ────────────────────────────────────────────────────────────────────

var (
	ErrEmptyCollection = errors.New("collection contains no tasks")
	ErrAnalysisFailed  = errors.New("analysis failed")
)

// ── MetricSnapshot ────────────────────────────────────────────────────────────

type MetricSnapshot struct {
	Total             int
	ByStatus          map[Status]int
	ByPriority        map[Priority]int
	CompletionRate    float64
	OverdueCount      int
	AvgAgeDays        float64
	PriorityDebtScore float64
}

func (s MetricSnapshot) String() string {
	return fmt.Sprintf(
		"Metrics{total=%d, done=%.0f%%, overdue=%d, debt=%.2f}",
		s.Total, s.CompletionRate*100, s.OverdueCount, s.PriorityDebtScore,
	)
}

// ── HealthReport ──────────────────────────────────────────────────────────────

type HealthReport struct {
	Snapshot        MetricSnapshot
	Warnings        []string
	Recommendations []string
}

func (h HealthReport) IsHealthy() bool { return len(h.Warnings) == 0 }

func (h HealthReport) Summary() string {
	if h.IsHealthy() {
		return "✅ Healthy"
	}
	msg := "⚠️ Issues:\n"
	for _, w := range h.Warnings {
		msg += "  - " + w + "\n"
	}
	return msg
}

// ── Analyzer ──────────────────────────────────────────────────────────────────

type Analyzer struct {
	manager *TaskManager
	// Pluggable scoring function — closures let callers customise scoring.
	ScoreFn func(t *Task) float64
}

func NewAnalyzer(manager *TaskManager) *Analyzer {
	defaultScore := func(t *Task) float64 { return t.Score() }
	return &Analyzer{manager: manager, ScoreFn: defaultScore}
}

func (a *Analyzer) Snapshot() (MetricSnapshot, error) {
	tasks := a.manager.All()
	if len(tasks) == 0 {
		return MetricSnapshot{}, ErrEmptyCollection
	}

	byStatus := make(map[Status]int)
	byPriority := make(map[Priority]int)
	totalAge := 0
	overdueCount := 0
	doneCount := 0

	for _, t := range tasks {
		byStatus[t.Status]++
		byPriority[t.Priority]++
		totalAge += t.AgeDays()
		if t.IsOverdue() {
			overdueCount++
		}
		if t.Status == StatusDone {
			doneCount++
		}
	}

	n := len(tasks)
	snapshot := MetricSnapshot{
		Total:             n,
		ByStatus:          byStatus,
		ByPriority:        byPriority,
		CompletionRate:    float64(doneCount) / float64(n),
		OverdueCount:      overdueCount,
		AvgAgeDays:        float64(totalAge) / float64(n),
		PriorityDebtScore: a.priorityDebt(tasks),
	}
	return snapshot, nil
}

func (a *Analyzer) HealthReport() (HealthReport, error) {
	snap, err := a.Snapshot()
	if err != nil {
		return HealthReport{}, fmt.Errorf("%w: %v", ErrAnalysisFailed, err)
	}
	report := HealthReport{Snapshot: snap}
	a.populateWarnings(&report)
	return report, nil
}

func (a *Analyzer) Rank(topN int) []*Task {
	return a.manager.RankByScore(topN)
}

// DetectPatterns returns named groups of tasks matching various antipatterns.
func (a *Analyzer) DetectPatterns() map[string][]*Task {
	// Using closures to define each pattern inline
	patterns := map[string]func(*Task) bool{
		"stale_todo": func(t *Task) bool {
			return t.Status == StatusTodo && t.AgeDays() > 30
		},
		"high_priority_blocked": func(t *Task) bool {
			return t.Status == StatusBlocked && t.Priority.IsUrgent()
		},
		"overdue_critical": func(t *Task) bool {
			return t.IsOverdue() && t.Priority == PriorityCritical
		},
		"zero_progress_subtasks": func(t *Task) bool {
			return len(t.Subtasks) > 0 && t.CompletionRate() == 0 && t.AgeDays() > 7
		},
	}

	result := make(map[string][]*Task, len(patterns))
	for name, pred := range patterns {
		result[name] = a.manager.Filter(pred)
	}
	return result
}

// WithCustomScorer returns a new Analyzer using a custom scoring closure.
func (a *Analyzer) WithCustomScorer(fn func(*Task) float64) *Analyzer {
	return &Analyzer{manager: a.manager, ScoreFn: fn}
}

// ── Private ───────────────────────────────────────────────────────────────────

func (a *Analyzer) priorityDebt(tasks []*Task) float64 {
	debt := 0.0
	for _, t := range tasks {
		if t.Priority.IsUrgent() && !t.Status.IsTerminal() {
			debt += float64(t.Priority.Weight()) * math.Log1p(float64(t.AgeDays()))
		}
	}
	return math.Round(debt*100) / 100
}

func (a *Analyzer) populateWarnings(report *HealthReport) {
	s := report.Snapshot
	if s.OverdueCount >= 10 {
		report.Warnings = append(report.Warnings, fmt.Sprintf("%d overdue tasks", s.OverdueCount))
		report.Recommendations = append(report.Recommendations, "Triage overdue tasks immediately")
	}
	if s.CompletionRate < 0.3 {
		report.Warnings = append(report.Warnings, fmt.Sprintf("Low completion: %.0f%%", s.CompletionRate*100))
		report.Recommendations = append(report.Recommendations, "Break large tasks into subtasks")
	}
	if s.PriorityDebtScore > 100 {
		report.Warnings = append(report.Warnings, fmt.Sprintf("High priority debt: %.1f", s.PriorityDebtScore))
	}
}

// ── Dead code ─────────────────────────────────────────────────────────────────

// legacyAverageScore was replaced by Rank(). Never called.
func (a *Analyzer) legacyAverageScore() float64 {
	tasks := a.manager.All()
	if len(tasks) == 0 {
		return 0
	}
	total := 0.0
	for _, t := range tasks {
		total += a.ScoreFn(t)
	}
	return total / float64(len(tasks))
}
