# main.rb — Entry point for Ruby task management showcase
# Showcases: Classes, Modules, Blocks, Lambdas, Enumerables, Error Handling

require_relative 'models'
require_relative 'analyzer'

module TaskSystem
  class CLI
    include Analyzer # Mixing in analysis capabilities

    def initialize(name)
      @name = name
      @tasks = []
    end

    def add_task(task)
      @tasks << task
    end

    def run_demo
      puts "=== #{@name} Demo ==="
      
      # 1. Setup sample data
      setup_samples

      # 2. Demonstrate Enumerable + Blocks
      puts "\n--- Active Tasks (Priority > MEDIUM) ---"
      high_priority = @tasks.select { |t| t.priority.weight > 2 && !t.status.terminal? }
      high_priority.each { |t| puts "  - #{t}" }

      # 3. Demonstrate Lambdas for custom filtering
      overdue_filter = ->(t) { t.overdue? }
      puts "\n--- Overdue Tasks ---"
      @tasks.filter(&overdue_filter).each { |t| puts "  [!] #{t.title}" }

      # 4. Demonstrate Analyzer Mixin
      puts "\n--- System Metrics ---"
      metrics = analyze_collection(@tasks)
      puts "  Total Tasks:    #{metrics[:total]}"
      puts "  Completion:     #{(metrics[:completion_rate] * 100).round(2)}%"
      puts "  Avg Urgency:    #{metrics[:avg_urgency].round(2)}"

      # 5. Demonstrate Error Handling
      begin
        puts "\nAttempting invalid transition..."
        @tasks.last.transition(:done)
        @tasks.last.transition(:todo) # Should fail if done is terminal
      rescue ArgumentError => e
        puts "  Caught expected error: #{e.message}"
      end
    end

    private

    def setup_samples
      t1 = Task.new("Implement IR Parser", priority: :critical)
      t2 = Task.new("Write Documentation", priority: :low)
      t3 = Task.new("Fix Memory Leak", priority: :high)
      
      t1.add_tag("core", "#ff0000")
      t3.add_tag("bug", "#00ff00")

      # Simulate some age/status
      t1.transition(:in_progress)
      
      # Nesting
      sub = Task.new("C++ support", priority: :medium)
      t1.add_subtask(sub)

      @tasks.concat([t1, t2, t3])
    end

    # ── Dead Code Demo ────────────────────────────────────────────────────────
    
    def legacy_report_generator(tasks)
      # This method is never called in run_demo.
      # It exists to test Polycode's dead code detection.
      tasks.each { |t| puts t.to_h }
    end
  end
end

if __FILE__ == $0
  app = TaskSystem::CLI.new("Polycode Ruby Showcase")
  app.run_demo
end
