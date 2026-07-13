# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

def create_search_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fact_fts USING fts5(
          project_id UNINDEXED,
          fact,
          source,
          category,
          scope,
          evidence
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS reflection_fts USING fts5(
          project_id UNINDEXED,
          task,
          summary,
          mistake,
          lesson,
          future_rule,
          task_type,
          outcome,
          problem,
          reasoning_summary,
          context_used,
          what_worked,
          what_failed,
          hidden_assumptions,
          negative_preconditions,
          useful_followup_focus,
          useful_followup_terms,
          misleading_followup_terms,
          inspection_targets,
          final_verification_path,
          related_cases,
          verification_method,
          reuse_feedback,
          source_cases,
          skill_candidate,
          trigger_condition,
          anti_pattern,
          repair_action,
          evidence
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS episode_fts USING fts5(
          project_id UNINDEXED,
          task,
          summary,
          outcome,
          files_touched,
          commands_run
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_file_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          summary,
          language,
          business_summary,
          business_terms
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_symbol_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          symbol,
          symbol_type,
          summary,
          business_summary,
          business_terms
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS code_log_fts USING fts5(
          project_id UNINDEXED,
          file_path,
          function,
          level,
          logger,
          message_template,
          raw_statement,
          business_summary,
          business_terms,
          business_event,
          trigger_stage,
          symptom_terms,
          likely_causes,
          process_hint,
          neighbor_terms
        );
        """
    )
    create_search_triggers(conn)
    rebuild_search_indexes(conn)



def create_search_triggers(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_ai AFTER INSERT ON semantic_facts BEGIN
          INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.fact, ''), COALESCE(new.source, ''), COALESCE(new.category, ''), COALESCE(new.scope, ''), COALESCE(new.evidence, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_ad AFTER DELETE ON semantic_facts BEGIN
          DELETE FROM semantic_fact_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS semantic_fact_fts_au AFTER UPDATE ON semantic_facts BEGIN
          DELETE FROM semantic_fact_fts WHERE rowid = old.id;
          INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.fact, ''), COALESCE(new.source, ''), COALESCE(new.category, ''), COALESCE(new.scope, ''), COALESCE(new.evidence, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS reflection_fts_ai AFTER INSERT ON reflections BEGIN
          INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.mistake, ''), COALESCE(new.lesson, ''), COALESCE(new.future_rule, ''), COALESCE(new.task_type, ''), COALESCE(new.outcome, ''), COALESCE(new.problem, ''), COALESCE(new.reasoning_summary, ''), COALESCE(new.context_used, ''), COALESCE(new.what_worked, ''), COALESCE(new.what_failed, ''), COALESCE(new.hidden_assumptions, ''), COALESCE(new.negative_preconditions, ''), COALESCE(new.useful_followup_focus, ''), COALESCE(new.useful_followup_terms, ''), COALESCE(new.misleading_followup_terms, ''), COALESCE(new.inspection_targets, ''), COALESCE(new.final_verification_path, ''), COALESCE(new.related_cases, ''), COALESCE(new.verification_method, ''), COALESCE(new.reuse_feedback, ''), COALESCE(new.source_cases, ''), COALESCE(new.skill_candidate, ''), COALESCE(new.trigger_condition, ''), COALESCE(new.anti_pattern, ''), COALESCE(new.repair_action, ''), COALESCE(new.evidence, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS reflection_fts_ad AFTER DELETE ON reflections BEGIN
          DELETE FROM reflection_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS reflection_fts_au AFTER UPDATE ON reflections BEGIN
          DELETE FROM reflection_fts WHERE rowid = old.id;
          INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.mistake, ''), COALESCE(new.lesson, ''), COALESCE(new.future_rule, ''), COALESCE(new.task_type, ''), COALESCE(new.outcome, ''), COALESCE(new.problem, ''), COALESCE(new.reasoning_summary, ''), COALESCE(new.context_used, ''), COALESCE(new.what_worked, ''), COALESCE(new.what_failed, ''), COALESCE(new.hidden_assumptions, ''), COALESCE(new.negative_preconditions, ''), COALESCE(new.useful_followup_focus, ''), COALESCE(new.useful_followup_terms, ''), COALESCE(new.misleading_followup_terms, ''), COALESCE(new.inspection_targets, ''), COALESCE(new.final_verification_path, ''), COALESCE(new.related_cases, ''), COALESCE(new.verification_method, ''), COALESCE(new.reuse_feedback, ''), COALESCE(new.source_cases, ''), COALESCE(new.skill_candidate, ''), COALESCE(new.trigger_condition, ''), COALESCE(new.anti_pattern, ''), COALESCE(new.repair_action, ''), COALESCE(new.evidence, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS episode_fts_ai AFTER INSERT ON episodes BEGIN
          INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.outcome, ''), COALESCE(new.files_touched, ''), COALESCE(new.commands_run, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS episode_fts_ad AFTER DELETE ON episodes BEGIN
          DELETE FROM episode_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS episode_fts_au AFTER UPDATE ON episodes BEGIN
          DELETE FROM episode_fts WHERE rowid = old.id;
          INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
          VALUES (new.id, new.project_id, COALESCE(new.task, ''), COALESCE(new.summary, ''), COALESCE(new.outcome, ''), COALESCE(new.files_touched, ''), COALESCE(new.commands_run, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_file_fts_ai AFTER INSERT ON code_files BEGIN
          INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.summary, ''), COALESCE(new.language, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_file_fts_ad AFTER DELETE ON code_files BEGIN
          DELETE FROM code_file_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_file_fts_au AFTER UPDATE ON code_files BEGIN
          DELETE FROM code_file_fts WHERE rowid = old.id;
          INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.summary, ''), COALESCE(new.language, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_ai AFTER INSERT ON code_symbols BEGIN
          INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.symbol, ''), COALESCE(new.symbol_type, ''), COALESCE(new.summary, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_ad AFTER DELETE ON code_symbols BEGIN
          DELETE FROM code_symbol_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_symbol_fts_au AFTER UPDATE ON code_symbols BEGIN
          DELETE FROM code_symbol_fts WHERE rowid = old.id;
          INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.symbol, ''), COALESCE(new.symbol_type, ''), COALESCE(new.summary, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS code_log_fts_ai AFTER INSERT ON code_log_statements BEGIN
          INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.function, ''), COALESCE(new.level, ''), COALESCE(new.logger, ''), COALESCE(new.message_template, ''), COALESCE(new.raw_statement, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''), COALESCE(new.business_event, ''), COALESCE(new.trigger_stage, ''), COALESCE(new.symptom_terms, ''), COALESCE(new.likely_causes, ''), COALESCE(new.process_hint, ''), COALESCE(new.neighbor_terms, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS code_log_fts_ad AFTER DELETE ON code_log_statements BEGIN
          DELETE FROM code_log_fts WHERE rowid = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS code_log_fts_au AFTER UPDATE ON code_log_statements BEGIN
          DELETE FROM code_log_fts WHERE rowid = old.id;
          INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
          VALUES (new.id, new.project_id, COALESCE(new.file_path, ''), COALESCE(new.function, ''), COALESCE(new.level, ''), COALESCE(new.logger, ''), COALESCE(new.message_template, ''), COALESCE(new.raw_statement, ''), COALESCE(new.business_summary, ''), COALESCE(new.business_terms, ''), COALESCE(new.business_event, ''), COALESCE(new.trigger_stage, ''), COALESCE(new.symptom_terms, ''), COALESCE(new.likely_causes, ''), COALESCE(new.process_hint, ''), COALESCE(new.neighbor_terms, ''));
        END;
        """
    )



def rebuild_search_indexes(conn: sqlite3.Connection) -> None:
    tables = (
        "semantic_fact_fts",
        "reflection_fts",
        "episode_fts",
        "code_file_fts",
        "code_symbol_fts",
        "code_log_fts",
    )
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        """
        INSERT INTO semantic_fact_fts(rowid, project_id, fact, source, category, scope, evidence)
        SELECT id, project_id, COALESCE(fact, ''), COALESCE(source, ''), COALESCE(category, ''), COALESCE(scope, ''), COALESCE(evidence, '')
        FROM semantic_facts
        """
    )
    conn.execute(
        """
        INSERT INTO reflection_fts(rowid, project_id, task, summary, mistake, lesson, future_rule, task_type, outcome, problem, reasoning_summary, context_used, what_worked, what_failed, hidden_assumptions, negative_preconditions, useful_followup_focus, useful_followup_terms, misleading_followup_terms, inspection_targets, final_verification_path, related_cases, verification_method, reuse_feedback, source_cases, skill_candidate, trigger_condition, anti_pattern, repair_action, evidence)
        SELECT id, project_id, COALESCE(task, ''), COALESCE(summary, ''), COALESCE(mistake, ''), COALESCE(lesson, ''), COALESCE(future_rule, ''), COALESCE(task_type, ''), COALESCE(outcome, ''), COALESCE(problem, ''), COALESCE(reasoning_summary, ''), COALESCE(context_used, ''), COALESCE(what_worked, ''), COALESCE(what_failed, ''), COALESCE(hidden_assumptions, ''), COALESCE(negative_preconditions, ''), COALESCE(useful_followup_focus, ''), COALESCE(useful_followup_terms, ''), COALESCE(misleading_followup_terms, ''), COALESCE(inspection_targets, ''), COALESCE(final_verification_path, ''), COALESCE(related_cases, ''), COALESCE(verification_method, ''), COALESCE(reuse_feedback, ''), COALESCE(source_cases, ''), COALESCE(skill_candidate, ''), COALESCE(trigger_condition, ''), COALESCE(anti_pattern, ''), COALESCE(repair_action, ''), COALESCE(evidence, '')
        FROM reflections
        """
    )
    conn.execute(
        """
        INSERT INTO episode_fts(rowid, project_id, task, summary, outcome, files_touched, commands_run)
        SELECT id, project_id, COALESCE(task, ''), COALESCE(summary, ''), COALESCE(outcome, ''), COALESCE(files_touched, ''), COALESCE(commands_run, '')
        FROM episodes
        """
    )
    conn.execute(
        """
        INSERT INTO code_file_fts(rowid, project_id, file_path, summary, language, business_summary, business_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(summary, ''), COALESCE(language, ''), COALESCE(business_summary, ''), COALESCE(business_terms, '')
        FROM code_files
        """
    )
    conn.execute(
        """
        INSERT INTO code_symbol_fts(rowid, project_id, file_path, symbol, symbol_type, summary, business_summary, business_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(symbol, ''), COALESCE(symbol_type, ''), COALESCE(summary, ''), COALESCE(business_summary, ''), COALESCE(business_terms, '')
        FROM code_symbols
        """
    )
    conn.execute(
        """
        INSERT INTO code_log_fts(rowid, project_id, file_path, function, level, logger, message_template, raw_statement, business_summary, business_terms, business_event, trigger_stage, symptom_terms, likely_causes, process_hint, neighbor_terms)
        SELECT id, project_id, COALESCE(file_path, ''), COALESCE(function, ''), COALESCE(level, ''), COALESCE(logger, ''), COALESCE(message_template, ''), COALESCE(raw_statement, ''), COALESCE(business_summary, ''), COALESCE(business_terms, ''), COALESCE(business_event, ''), COALESCE(trigger_stage, ''), COALESCE(symptom_terms, ''), COALESCE(likely_causes, ''), COALESCE(process_hint, ''), COALESCE(neighbor_terms, '')
        FROM code_log_statements
        """
    )
