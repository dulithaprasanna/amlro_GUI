from pathlib import Path

import pytest

from amlro_gui.exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
    InvalidExperimentIdError,
)
from amlro_gui.schemas.config import ExperimentConfig
from amlro_gui.services import experiment_service


def test_create_and_load_state_round_trips(tmp_path):
    state = experiment_service.create_experiment(tmp_path, mode="new")

    loaded = experiment_service.load_state(tmp_path, state.id)

    assert loaded == state


def test_save_state_persists_config(tmp_path):
    state = experiment_service.create_experiment(tmp_path, mode="new")
    state.config = ExperimentConfig(
        objectives=["Yield"],
        directions=["max"],
    )
    state.progress.reaction_scope = True

    experiment_service.save_state(tmp_path, state)
    reloaded = experiment_service.load_state(tmp_path, state.id)

    assert reloaded.config.objectives == ["Yield"]
    assert reloaded.progress.reaction_scope is True


def test_create_experiment_with_explicit_id(tmp_path):
    state = experiment_service.create_experiment(
        tmp_path, mode="old", experiment_id="my-first-run"
    )

    assert state.id == "my-first-run"
    assert (tmp_path / "my-first-run" / "state.json").exists()


def test_create_experiment_rejects_duplicate_id(tmp_path):
    experiment_service.create_experiment(tmp_path, mode="new", experiment_id="dup")

    with pytest.raises(ExperimentAlreadyExistsError):
        experiment_service.create_experiment(tmp_path, mode="new", experiment_id="dup")


def test_load_state_missing_experiment_raises(tmp_path):
    with pytest.raises(ExperimentNotFoundError):
        experiment_service.load_state(tmp_path, "does-not-exist")


@pytest.mark.parametrize(
    "bad_id",
    [
        "../escape",
        "..\\escape",
        "a/b",
        "a\\b",
        "with space",
        "",
    ],
)
def test_invalid_experiment_ids_are_rejected(tmp_path, bad_id):
    with pytest.raises(InvalidExperimentIdError):
        experiment_service.create_experiment(tmp_path, mode="new", experiment_id=bad_id)


def test_experiment_dir_for_absolute_escape_is_rejected(tmp_path):
    with pytest.raises(InvalidExperimentIdError):
        experiment_service.experiment_dir_for(tmp_path, "C:")


def test_list_experiments_returns_created_experiments(tmp_path):
    experiment_service.create_experiment(tmp_path, mode="new", experiment_id="run-a")
    experiment_service.create_experiment(tmp_path, mode="old", experiment_id="run-b")

    summaries = experiment_service.list_experiments(tmp_path)

    assert {summary.id for summary in summaries} == {"run-a", "run-b"}


def test_list_experiments_on_missing_workspace_root_returns_empty(tmp_path):
    missing = tmp_path / "does-not-exist-yet"

    assert experiment_service.list_experiments(missing) == []


def test_list_experiments_ignores_directories_without_state(tmp_path):
    (tmp_path / "not-an-experiment").mkdir()

    assert experiment_service.list_experiments(tmp_path) == []


def test_create_experiment_with_custom_exp_dir(tmp_path):
    workspace_root = tmp_path / "workspace"
    custom_dir = tmp_path / "somewhere" / "else" / "my-reactions"

    state = experiment_service.create_experiment(
        workspace_root,
        mode="new",
        experiment_id="custom-run",
        exp_dir=str(custom_dir),
    )

    assert state.exp_dir == str(custom_dir)
    assert (custom_dir / "state.json").exists()
    # The registry itself still lives under workspace_root, even though the
    # experiment's own data does not.
    assert (workspace_root / "registry.json").exists()

    loaded = experiment_service.load_state(workspace_root, "custom-run")
    assert loaded.exp_dir == str(custom_dir)


def test_create_experiment_rejects_folder_already_used_as_experiment(tmp_path):
    custom_dir = tmp_path / "shared-folder"
    experiment_service.create_experiment(
        tmp_path / "workspace-a", mode="new", experiment_id="a", exp_dir=str(custom_dir)
    )

    with pytest.raises(ExperimentAlreadyExistsError):
        experiment_service.create_experiment(
            tmp_path / "workspace-b",
            mode="new",
            experiment_id="b",
            exp_dir=str(custom_dir),
        )


def test_list_and_load_include_exp_dir(tmp_path):
    state = experiment_service.create_experiment(
        tmp_path, mode="new", experiment_id="run-a"
    )

    summaries = experiment_service.list_experiments(tmp_path)

    assert summaries[0].exp_dir == state.exp_dir


def test_list_experiments_orders_most_recently_updated_first(tmp_path):
    experiment_service.create_experiment(tmp_path, mode="new", experiment_id="oldest")
    experiment_service.create_experiment(tmp_path, mode="new", experiment_id="newest")

    # Touching "oldest" again after "newest" was created should bump it back
    # to the top — "most recent" means most recently worked on, not just
    # whichever experiment happened to be created first.
    oldest = experiment_service.load_state(tmp_path, "oldest")
    experiment_service.save_state(tmp_path, oldest)

    summaries = experiment_service.list_experiments(tmp_path)

    assert [summary.id for summary in summaries] == ["oldest", "newest"]


def test_remove_experiment_unregisters_but_keeps_files_by_default(tmp_path):
    state = experiment_service.create_experiment(
        tmp_path, mode="new", experiment_id="to-remove"
    )

    experiment_service.remove_experiment(tmp_path, "to-remove")

    assert experiment_service.list_experiments(tmp_path) == []
    assert (Path(state.exp_dir) / "state.json").exists()


def test_remove_experiment_can_also_delete_files(tmp_path):
    state = experiment_service.create_experiment(
        tmp_path, mode="new", experiment_id="to-delete"
    )

    experiment_service.remove_experiment(tmp_path, "to-delete", delete_files=True)

    assert experiment_service.list_experiments(tmp_path) == []
    assert not Path(state.exp_dir).exists()


def test_remove_experiment_missing_raises(tmp_path):
    with pytest.raises(ExperimentNotFoundError):
        experiment_service.remove_experiment(tmp_path, "does-not-exist")


def test_scan_for_experiments_registers_unregistered_folders(tmp_path):
    workspace_root = tmp_path / "workspace"
    scan_root = tmp_path / "elsewhere"
    scan_root.mkdir()

    # Created directly against its own folder's workspace so it never
    # touches workspace_root's registry — simulates an experiment that
    # exists on disk but isn't known to this workspace yet.
    experiment_service.create_experiment(
        scan_root / "_unused_registry",
        mode="old",
        experiment_id="found-run",
        exp_dir=str(scan_root / "found-run"),
    )

    result = experiment_service.scan_for_experiments(workspace_root, str(scan_root))

    assert [summary.id for summary in result["added"]] == ["found-run"]
    assert result["skipped"] == []
    assert {s.id for s in experiment_service.list_experiments(workspace_root)} == {
        "found-run"
    }


def test_scan_for_experiments_skips_already_registered(tmp_path):
    state = experiment_service.create_experiment(
        tmp_path, mode="new", experiment_id="already-here"
    )

    result = experiment_service.scan_for_experiments(tmp_path, state.exp_dir)

    assert result["added"] == []
    assert result["skipped"] == []


def test_scan_for_experiments_skips_id_collision(tmp_path):
    workspace_root = tmp_path / "workspace"
    experiment_service.create_experiment(
        workspace_root, mode="new", experiment_id="dup-id"
    )

    scan_root = tmp_path / "elsewhere"
    scan_root.mkdir()
    experiment_service.create_experiment(
        scan_root / "_unused_registry",
        mode="new",
        experiment_id="dup-id",
        exp_dir=str(scan_root / "dup-id"),
    )

    result = experiment_service.scan_for_experiments(workspace_root, str(scan_root))

    assert result["added"] == []
    assert len(result["skipped"]) == 1
    assert "dup-id" in result["skipped"][0]["reason"]


def test_scan_for_experiments_rejects_missing_folder(tmp_path):
    with pytest.raises(InvalidExperimentIdError):
        experiment_service.scan_for_experiments(tmp_path, str(tmp_path / "nope"))
