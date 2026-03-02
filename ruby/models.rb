# models.rb — Task domain model in Ruby
# Showcases: classes, modules, mixins, attr_accessor, comparable, enumerable, Struct
# frozen_string_literal: true

require 'securerandom'
require 'time'

# ── Modules / Mixins ──────────────────────────────────────────────────────────

module Scorable
  def score
    raise NotImplementedError, "#{self.class}#score not implemented"
  end
end

module Describable
  def describe
    "#{self.class.name}(#{respond_to?(:title) ? title : id})"
  end
end

module Auditable
  def self.included(base)
    base.instance_variable_set(:@audit_log, [])
    base.extend(ClassMethods)
  end

  module ClassMethods
    def audit_log
      @audit_log ||= []
    end
  end

  def audit(action, actor: 'system')
    self.class.audit_log << { action: action, actor: actor, at: Time.now.utc }
  end
end

# ── Priority ──────────────────────────────────────────────────────────────────

module Priority
  LOW      = :low
  MEDIUM   = :medium
  HIGH     = :high
  CRITICAL = :critical

  WEIGHTS = {
    LOW      => 1,
    MEDIUM   => 2,
    HIGH     => 4,
    CRITICAL => 8,
  }.freeze

  ALL = WEIGHTS.keys.freeze

  def self.weight(priority)
    WEIGHTS.fetch(priority) { raise ArgumentError, "Unknown priority: #{priority}" }
  end

  def self.urgent?(priority)
    weight(priority) >= WEIGHTS[HIGH]
  end
end

# ── Status ────────────────────────────────────────────────────────────────────

module Status
  TODO        = :todo
  IN_PROGRESS = :in_progress
  BLOCKED     = :blocked
  DONE        = :done
  CANCELLED   = :cancelled

  TERMINAL = [DONE, CANCELLED].freeze
  ACTIVE   = [TODO, IN_PROGRESS, BLOCKED].freeze

  def self.terminal?(status)
    TERMINAL.include?(status)
  end
end

# ── Tag ───────────────────────────────────────────────────────────────────────

Tag = Struct.new(:name, :color, keyword_init: true) do
  def initialize(name:, color: '#888888')
    raise ArgumentError, 'tag name cannot be empty' if name.to_s.strip.empty?
    super
  end

  def to_s
    "##{name}"
  end

  def ==(other)
    other.is_a?(Tag) && name == other.name
  end
  alias eql? ==

  def hash
    name.hash
  end
end

# ── Task ──────────────────────────────────────────────────────────────────────

class Task
  include Comparable
  include Scorable
  include Describable
  include Auditable

  attr_reader :id, :created_at
  attr_accessor :title, :description, :priority, :status, :due_date, :updated_at

  def initialize(title, priority: Priority::MEDIUM, description: '')
    raise ArgumentError, 'title cannot be empty' if title.to_s.strip.empty?

    @id          = SecureRandom.uuid
    @title       = title.strip
    @description = description
    @priority    = priority
    @status      = Status::TODO
    @tags        = []
    @subtasks    = []
    @due_date    = nil
    @created_at  = Time.now.utc
    @updated_at  = @created_at

    audit('CREATED')
  end

  # ── Computed properties ────────────────────────────────────────────────

  def overdue?
    return false if due_date.nil? || Status.terminal?(status)
    Time.now.utc > due_date
  end

  def age_days
    ((Time.now.utc - created_at) / 86_400).to_i
  end

  def completion_rate
    return (status == Status::DONE ? 1.0 : 0.0) if @subtasks.empty?
    done = @subtasks.count { |t| t.status == Status::DONE }
    done.to_f / @subtasks.size
  end

  def estimate_effort
    base         = Priority.weight(priority) * 2
    sub_penalty  = @subtasks.size / 3
    due_penalty  = overdue? ? 1 : 0
    base + sub_penalty + due_penalty
  end

  def score
    base     = Priority.weight(priority) * 10.0
    age_f    = Math.log1p(age_days) * 2.0
    overdue  = overdue? ? 20.0 : 0.0
    effort   = estimate_effort * 0.5
    base + age_f + overdue - effort
  end

  # ── Mutation ──────────────────────────────────────────────────────────

  def transition!(new_status)
    raise "Cannot transition from terminal status #{status}" if Status.terminal?(status)
    self.status = new_status
    touch!
    audit("STATUS_CHANGED:#{new_status}")
    self
  end

  def add_subtask(task)
    @subtasks << task
    touch!
  end

  def add_tag(tag)
    @tags << tag unless @tags.include?(tag)
  end

  def remove_tag(name)
    @tags.reject! { |t| t.name == name.to_s }
  end

  def tags
    @tags.dup.freeze
  end

  def subtasks
    @subtasks.dup.freeze
  end

  # ── Comparable ────────────────────────────────────────────────────────

  def <=>(other)
    return nil unless other.is_a?(Task)
    Priority.weight(other.priority) <=> Priority.weight(priority) # higher priority first
  end

  def ==(other)
    other.is_a?(Task) && id == other.id
  end

  def hash
    id.hash
  end

  # ── Serialisation ─────────────────────────────────────────────────────

  def to_h
    {
      id:               id,
      title:            title,
      description:      description,
      priority:         priority,
      status:           status,
      overdue:          overdue?,
      age_days:         age_days,
      completion_rate:  completion_rate.round(3),
      tags:             tags.map(&:name),
    }
  end

  def to_s
    "Task[#{id[0, 8]}] #{title} (#{status}/#{priority})"
  end

  def inspect
    "#<Task id=#{id[0, 8].inspect} title=#{title.inspect} status=#{status} priority=#{priority}>"
  end

  private

  def touch!
    self.updated_at = Time.now.utc
  end
end

# ── TaskCollection ────────────────────────────────────────────────────────────

class TaskCollection
  include Enumerable

  attr_reader :name

  def initialize(name)
    @name  = name
    @index = {}
  end

  def add(task)
    @index[task.id] = task
    self
  end

  def [](id)
    @index[id]
  end

  def remove(id)
    @index.delete(id)
  end

  def each(&block)
    @index.values.each(&block)
  end

  def size
    @index.size
  end

  def empty?
    @index.empty?
  end

  def group_by_status
    group_by(&:status)
  end

  def sort_by_priority
    sort.to_a
  end

  def to_s
    "TaskCollection[#{name}](#{size} tasks)"
  end
end
