"""LoRP-FSD PyVRP v3 — Phase 1: data and C-compatible preprocessing.

This package replicates the C/Gurobi LoRP-FSD model (``det_LoRP_DSD``) for
benchmarking against ``results_MILP.xlsx`` (sheet ``LoRP-FSD``). Phase 1 covers
parsing, scaling, facility sizing, and fixed-facility design construction.

Source of truth: ``docs/C_SOLVER_AUDIT.md``, ``docs/PYVRP_REPLICATION_SPEC.md``,
``docs/IMPLEMENTATION_PLAN.md``, ``docs/C_CONGRUENCY_TEST.md``.

Phase 1 deliberately does NOT import any legacy root modules.
"""

from __future__ import annotations

from .da_options import (
    DAOption,
    build_da_options,
    clients_with_da,
    da_options_by_depot,
    da_pairs,
)
from .dat_parser import (
    ClientNode,
    DEFAULT_INSTANCE_FOLDERS,
    DepotNode,
    InstanceResolution,
    ParsedInstance,
    parse_dat,
    resolve_dat_path,
)
from .excel_loader import load_lorp_fsd_rows, load_row
from .experiment_config import (
    ExperimentConfig,
    SelectedDepot,
    SUPPORTED_PROBLEM_ID,
)
from .facility_sizing import (
    FACILITY_SIZE_COUNT,
    SIZE_MULTIPLIERS,
    size_capacity,
    size_cost,
)
from .geometry import Point, euclidean
from .instance import FacilityDesign, FacilityDesignDepot, build_facility_design
from .pyvrp_builder import (
    BuildInfo,
    ForbiddenRoutingAssignments,
    RoutingVehicleSpec,
    VehicleTypeMeta,
    build_relaxed_model,
    routing_vehicle_specs,
)
from .scaling import PYVRP_INT_SCALE, ScaledGeometry, build_scaled_geometry
from .solution_parser import (
    DA_BINDING_VIOLATION,
    DAAssignmentRecord,
    ParsedSolution,
    RouteRecord,
    parse_solution,
)
from .cost_reconstruction import (
    CostBreakdown,
    ComparisonMetric,
    comparison_metric,
    reconstruct_cost,
)
from .capacity_audit import CapacityAudit, DepotAuditRecord, audit_capacity
from .feasibility import (
    FeasibilityReport,
    PENALTY_DISTANCE_SUSPECTED,
    audit_feasibility,
    client_has_service_option,
    client_has_length_feasible_service_option,
    make_feasibility_checker,
    penalty_distance_threshold,
)
from .repair import (
    REPAIR_INFEASIBLE,
    REPAIR_POLICY_BASELINE,
    REPAIR_POLICY_SAFE_BOTH,
    REPAIR_POLICY_SAFE_CAPACITY_RELEASE,
    REPAIR_POLICY_SAFE_LENGTH,
    REJECTION_NO_LENGTH_ALTERNATIVE,
    REJECTION_SAME_DEPOT_DA_RISK,
    REJECTION_STRANDS_CLIENT,
    RepairCandidate,
    RepairCandidateSafety,
    RepairSelection,
    build_repair_candidates,
    compute_route_savings,
    diagnose_repair_candidate,
    select_forbidden_assignments,
)
from .artifacts import iteration_dir, write_iteration_artifacts
from .runner import (
    IterationResult,
    RowRunResult,
    STATUS_FEASIBLE,
    STATUS_MAX_ITERATIONS,
    STATUS_REPAIR_INFEASIBLE,
    STATUS_STUCK_NONCAPACITY,
    compute_repair_step,
    run_row,
    run_row_from_excel,
)
from .batch import (
    CONSOLIDATED_COLUMNS,
    STATUS_ERROR,
    STATUS_TIMEOUT,
    RowRecord,
    build_error_record,
    build_row_record,
    build_timeout_record,
    run_rows,
    summarize,
    write_consolidated_csv,
    write_consolidated_excel,
    write_summary,
    write_summary_markdown,
)

__all__ = [
    "ClientNode",
    "DepotNode",
    "DEFAULT_INSTANCE_FOLDERS",
    "InstanceResolution",
    "ParsedInstance",
    "parse_dat",
    "resolve_dat_path",
    "load_lorp_fsd_rows",
    "load_row",
    "ExperimentConfig",
    "SelectedDepot",
    "SUPPORTED_PROBLEM_ID",
    "FACILITY_SIZE_COUNT",
    "SIZE_MULTIPLIERS",
    "size_capacity",
    "size_cost",
    "Point",
    "euclidean",
    "FacilityDesign",
    "FacilityDesignDepot",
    "build_facility_design",
    "PYVRP_INT_SCALE",
    "ScaledGeometry",
    "build_scaled_geometry",
    "DAOption",
    "build_da_options",
    "da_pairs",
    "da_options_by_depot",
    "clients_with_da",
    "BuildInfo",
    "ForbiddenRoutingAssignments",
    "RoutingVehicleSpec",
    "VehicleTypeMeta",
    "build_relaxed_model",
    "routing_vehicle_specs",
    "DA_BINDING_VIOLATION",
    "DAAssignmentRecord",
    "ParsedSolution",
    "RouteRecord",
    "parse_solution",
    "CostBreakdown",
    "ComparisonMetric",
    "comparison_metric",
    "reconstruct_cost",
    "CapacityAudit",
    "DepotAuditRecord",
    "audit_capacity",
    "FeasibilityReport",
    "PENALTY_DISTANCE_SUSPECTED",
    "audit_feasibility",
    "client_has_service_option",
    "client_has_length_feasible_service_option",
    "make_feasibility_checker",
    "penalty_distance_threshold",
    "REPAIR_INFEASIBLE",
    "REPAIR_POLICY_BASELINE",
    "REPAIR_POLICY_SAFE_BOTH",
    "REPAIR_POLICY_SAFE_CAPACITY_RELEASE",
    "REPAIR_POLICY_SAFE_LENGTH",
    "REJECTION_NO_LENGTH_ALTERNATIVE",
    "REJECTION_SAME_DEPOT_DA_RISK",
    "REJECTION_STRANDS_CLIENT",
    "RepairCandidate",
    "RepairCandidateSafety",
    "RepairSelection",
    "build_repair_candidates",
    "compute_route_savings",
    "diagnose_repair_candidate",
    "select_forbidden_assignments",
    "iteration_dir",
    "write_iteration_artifacts",
    "IterationResult",
    "RowRunResult",
    "STATUS_FEASIBLE",
    "STATUS_MAX_ITERATIONS",
    "STATUS_REPAIR_INFEASIBLE",
    "STATUS_STUCK_NONCAPACITY",
    "compute_repair_step",
    "run_row",
    "run_row_from_excel",
    "CONSOLIDATED_COLUMNS",
    "STATUS_ERROR",
    "STATUS_TIMEOUT",
    "RowRecord",
    "build_error_record",
    "build_row_record",
    "build_timeout_record",
    "run_rows",
    "summarize",
    "write_consolidated_csv",
    "write_consolidated_excel",
    "write_summary",
    "write_summary_markdown",
]
