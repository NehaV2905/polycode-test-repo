// manager.go — Task manager with goroutines, channels, and context
// Showcases: goroutines, channels, select, context, sync, generics (Go 1.21+)
package taskmanager

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"sync"
)

// ── Manager interface ─────────────────────────────────────────────────────────

type Manager interface {
	Add(task *Task) error
	Get(id string) (*Task, bool)
	Remove(id string) bool
	All() []*Task
	Filter(pred func(*Task) bool) []*Task
}

// ── TaskManager ───────────────────────────────────────────────────────────────

type TaskManager struct {
	mu    sync.RWMutex
	store map[string]*Task
	name  string
}

func NewTaskManager(name string) *TaskManager {
	return &TaskManager{
		name:  name,
		store: make(map[string]*Task),
	}
}

// ── CRUD ──────────────────────────────────────────────────────────────────────

func (m *TaskManager) Add(task *Task) error {
	if task == nil {
		return errors.New("task must not be nil")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.store[task.ID] = task
	return nil
}

func (m *TaskManager) Get(id string) (*Task, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	t, ok := m.store[id]
	return t, ok
}

func (m *TaskManager) Remove(id string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	_, ok := m.store[id]
	if ok {
		delete(m.store, id)
	}
	return ok
}

func (m *TaskManager) All() []*Task {
	m.mu.RLock()
	defer m.mu.RUnlock()
	tasks := make([]*Task, 0, len(m.store))
	for _, t := range m.store {
		tasks = append(tasks, t)
	}
	return tasks
}

func (m *TaskManager) Size() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.store)
}

// ── Query ─────────────────────────────────────────────────────────────────────

func (m *TaskManager) Filter(pred func(*Task) bool) []*Task {
	all := m.All()
	result := make([]*Task, 0)
	for _, t := range all {
		if pred(t) {
			result = append(result, t)
		}
	}
	return result
}

func (m *TaskManager) FindByStatus(statuses ...Status) []*Task {
	allowed := make(map[Status]struct{}, len(statuses))
	for _, s := range statuses {
		allowed[s] = struct{}{}
	}
	return m.Filter(func(t *Task) bool {
		_, ok := allowed[t.Status]
		return ok
	})
}

func (m *TaskManager) FindOverdue() []*Task {
	return m.Filter(func(t *Task) bool { return t.IsOverdue() })
}

func (m *TaskManager) RankByScore(topN int) []*Task {
	all := m.All()
	sort.Slice(all, func(i, j int) bool {
		return all[i].Score() > all[j].Score()
	})
	if topN > 0 && topN < len(all) {
		return all[:topN]
	}
	return all
}

func (m *TaskManager) GroupByStatus() map[Status][]*Task {
	groups := make(map[Status][]*Task)
	for _, t := range m.All() {
		groups[t.Status] = append(groups[t.Status], t)
	}
	return groups
}

// ── Concurrent processing ─────────────────────────────────────────────────────

// ProcessBatch runs a processing function over all tasks concurrently,
// collecting errors via a channel. Returns all errors encountered.
func (m *TaskManager) ProcessBatch(
	ctx context.Context,
	process func(ctx context.Context, t *Task) error,
	concurrency int,
) []error {
	tasks := m.All()
	sem := make(chan struct{}, concurrency)
	errCh := make(chan error, len(tasks))
	var wg sync.WaitGroup

	for _, task := range tasks {
		task := task // capture loop variable
		wg.Add(1)
		go func() {
			defer wg.Done()
			select {
			case <-ctx.Done():
				errCh <- ctx.Err()
				return
			case sem <- struct{}{}:
				defer func() { <-sem }()
			}
			if err := process(ctx, task); err != nil {
				errCh <- fmt.Errorf("task %s: %w", task.ID[:8], err)
			}
		}()
	}

	wg.Wait()
	close(errCh)

	var errs []error
	for e := range errCh {
		errs = append(errs, e)
	}
	return errs
}

// Watch streams tasks matching pred into a channel until ctx is cancelled.
func (m *TaskManager) Watch(ctx context.Context, pred func(*Task) bool) <-chan *Task {
	ch := make(chan *Task, 16)
	go func() {
		defer close(ch)
		for _, task := range m.Filter(pred) {
			select {
			case <-ctx.Done():
				return
			case ch <- task:
			}
		}
	}()
	return ch
}

// ── Bulk mutation ─────────────────────────────────────────────────────────────

func (m *TaskManager) BulkTransition(pred func(*Task) bool, newStatus Status) int {
	count := 0
	for _, task := range m.Filter(pred) {
		if err := task.Transition(newStatus); err == nil {
			count++
		}
	}
	return count
}

func (m *TaskManager) String() string {
	return fmt.Sprintf("TaskManager{name=%q, size=%d}", m.name, m.Size())
}

// ── Dead code ─────────────────────────────────────────────────────────────────

// legacyLinearSearch was replaced by map-based lookup. Never called.
func (m *TaskManager) legacyLinearSearch(id string) *Task {
	for _, t := range m.store {
		if t.ID == id {
			return t
		}
	}
	return nil
}
