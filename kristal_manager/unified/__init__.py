"""Manager vNext: operational event journal, orchestration and materialized read model.

Kristals are authoritative; this package only persists derived observations.
"""
from .repository import (start_run, finish_run, list_runs, history, latest_observation,
                         dashboard, record_decision, list_decisions, integrity_check,
                         backfill_v1, backup_database)
__all__ = ['start_run','finish_run','list_runs','history','latest_observation','dashboard',
           'record_decision','list_decisions','integrity_check','backfill_v1','backup_database']
