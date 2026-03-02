# analyzer.rb — Metrics, health reports, and pattern detection in Ruby
# Showcases: blocks, Proc, lambda, method objects, Comparable, memoization, struct
# frozen_string_literal: true

require_relative 'models'
require 'forwardable'

# ── MetricSnapshot ────────────────────────────────────────────────────────────

MetricSnapshot = Struct.new(
  :total, :by_status, :by_priority,
  :completion_rate, :overdue_count, :avg_age_days, :priority_debt_score,
  keyword_init: true
) do
  def summary
    format(
      'total=%d, done=%.0f%%, overdue=%d, debt=%.2f',
      total, completion_rate * 100, overdue_count, priority_debt_score
    )
  end

  def to_h
    super.merge(completion_pct: (completion_rate * 100).round(1))
  end
end

# ── HealthReport ──────────────────────────────────────────────────────────────

class HealthReport
  THRESHOLDS = {
    critical_overdue: 10,
    high_backlog: 50,
    low_completion: 0.3,
  }.freeze

  attr_reader :snapshot, :warnings, :recommendations

  def initialize(snapshot)
    @snapshot        = snapshot
    @warnings        = []
    @recommendations = []
    evaluate!
  end

  def healthy?
    @warnings.empty?
  end

  def to_s
    return '✅ Healthy' if healthy?

    lines = ['⚠️ Issues detected:']
    @warnings.each { |w| lines << "  - #{w}" }
    lines << 'Recommendations:'
    @recommendations.each { |r| lines << "  → #{r}" }
    lines.join("\n")
  end

  private

  def evaluate!
    s = @snapshot
    if s.overdue_count >= THRESHOLDS[:critical_overdue]
      @warnings        << "#{s.overdue_count} overdue tasks — critical backlog"
      @recommendations << 'Triage overdue tasks immediately'
    end
    if s.completion_rate < THRESHOLDS[:low_completion]
      @warnings        << "Low completion rate: #{(s.completion_rate * 100).round}%"
      @recommendations << 'Break large tasks into smaller subtasks'
    end
    if s.total >= THRESHOLDS[:high_backlog]
      @warnings        << "Large backlog: #{s.total} tasks"
      @recommendations << 'Archive or cancel stale tasks'
    end
  end
end

# ── TaskAnalyzer ──────────────────────────────────────────────────────────────

class TaskAnalyzer
  extend Forwardable

  def_delegators :@collection, :each, :size, :empty?

  def initialize(collection)
    @collection = collection
    # Memoised internal cache
    @_snapshot = nil
  end

  # ── Metrics ───────────────────────────────────────────────────────────

  def snapshot
    @_snapshot ||= compute_snapshot
  end

  def health_report
    HealthReport.new(snapshot)
  end

  def invalidate_cache!
    @_snapshot = nil
  end

  # ── Scoring — demonstrates lambda and proc ────────────────────────────

  DEFAULT_SCORER = lambda do |task|
    base    = Priority.weight(task.priority) * 10.0
    age_f   = Math.log1p(task.age_days) * 2.0
    overdue = task.overdue? ? 20.0 : 0.0
    effort  = task.estimate_effort * 0.5
    base + age_f + overdue - effort
  end

  def rank(top_n: nil, scorer: DEFAULT_SCORER)
    active = @collection.select { |t| Status::ACTIVE.include?(t.status) }
    sorted = active.sort_by { |t| -scorer.call(t) }
    top_n ? sorted.first(top_n) : sorted
  end

  # ── Pattern detection — demonstrates blocks ───────────────────────────

  PATTERNS = {
    stale_todo:            ->(t) { t.status == Status::TODO && t.age_days > 30 },
    high_priority_blocked: ->(t) { t.status == Status::BLOCKED && Priority.urgent?(t.priority) },
    overdue_critical:      ->(t) { t.overdue? && t.priority == Priority::CRITICAL },
    zero_progress_large:   ->(t) { t.subtasks.size > 3 && t.completion_rate.zero? },
  }.freeze

  def detect_patterns
    PATTERNS.transform_values do |pred|
      @collection.select(&pred)
    end
  end

  def stale_tasks(min_age: 30)
    @collection.select { |t| t.status == Status::TODO && t.age_days >= min_age }
  end

  def tag_distribution
    @collection.each_with_object(Hash.new(0)) do |task, counts|
      task.tags.each { |tag| counts[tag.name] += 1 }
    end
  end

  # ── Enumerable-style API ──────────────────────────────────────────────

  def each_critical
    return enum_for(:each_critical) unless block_given?
    @collection.each do |task|
      yield task if task.priority == Priority::CRITICAL && !Status.terminal?(task.status)
    end
  end

  def map_scores(scorer: DEFAULT_SCORER)
    @collection.map { |t| [t, scorer.call(t)] }.to_h
  end

  # ── Private ───────────────────────────────────────────────────────────

  private

  def compute_snapshot
    tasks = @collection.to_a
    return MetricSnapshot.new(total: 0, by_status: {}, by_priority: {},
                               completion_rate: 0.0, overdue_count: 0,
                               avg_age_days: 0.0, priority_debt_score: 0.0) if tasks.empty?

    by_status   = tasks.group_by(&:status).transform_values(&:count)
    by_priority = tasks.group_by(&:priority).transform_values(&:count)
    done        = by_status.fetch(Status::DONE, 0)
    overdue     = tasks.count(&:overdue?)
    avg_age     = tasks.sum(&:age_days).to_f / tasks.size
    debt        = compute_priority_debt(tasks)

    MetricSnapshot.new(
      total:                tasks.size,
      by_status:            by_status,
      by_priority:          by_priority,
      completion_rate:      done.to_f / tasks.size,
      overdue_count:        overdue,
      avg_age_days:         avg_age.round(2),
      priority_debt_score:  debt.round(2),
    )
  end

  def compute_priority_debt(tasks)
    tasks.reduce(0.0) do |sum, task|
      next sum unless Priority.urgent?(task.priority) && !Status.terminal?(task.status)
      sum + Priority.weight(task.priority) * Math.log1p(task.age_days)
    end
  end

  # ── Dead code ──────────────────────────────────────────────────────────

  # Was an early text-only report. Never called in current code.
  def legacy_text_report
    "Total: #{snapshot.total}, Done: #{snapshot.by_status.fetch(Status::DONE, 0)}"
  end
end
