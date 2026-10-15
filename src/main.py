#!/usr/bin/env python3

import fnmatch
import shutil
from pathlib import Path

import click


ROOT_PATH = Path(__file__).resolve().parent.parent
PROFILES_PATH = ROOT_PATH / "profiles"
RULES_PATH = ROOT_PATH / "rules"


def _remove_path(path):
	if path.is_symlink() or path.is_file():
		path.unlink()
	elif path.is_dir():
		shutil.rmtree(path)


def _profile_files(profile):
	return (path for path in profile.rglob("*") if path.is_file() or path.is_symlink())


def _apply_profile(target, profile):
	for source in _profile_files(profile):
		relative = source.relative_to(profile)
		destination = target / relative
		destination.parent.mkdir(parents=True, exist_ok=True)
		if destination.exists() or destination.is_symlink():
			_remove_path(destination)
		destination.symlink_to(source)


def _remove_profile_links(target, profile):
	profile = profile.resolve()
	for path in target.rglob("*"):
		if not path.is_symlink():
			continue
		try:
			path.resolve().relative_to(profile)
		except ValueError:
			continue
		path.unlink()


def _rule_file(rules):
	if rules.is_dir():
		rules = rules / "default"
	if not rules.is_file():
		raise click.ClickException(f"rule file not found: {rules}")
	return rules


def _read_rules(rules):
	include = []
	exclude = []
	for line in _rule_file(rules).read_text().splitlines():
		line = line.strip()
		if not line or line.startswith("#") or line == "+":
			continue
		if line.startswith("-"):
			exclude.append(line[1:].strip().rstrip("/"))
		elif line.startswith("+"):
			include.append(line[1:].strip().rstrip("/"))
	return include, exclude


def _matches(relative, patterns):
	value = relative.as_posix()
	return any(fnmatch.fnmatch(value, pattern) or value.startswith(pattern + "/") for pattern in patterns)


def _save_profile(target, profile, rules):
	if profile.exists():
		_remove_path(profile)
	profile.mkdir(parents=True)
	include, exclude = _read_rules(rules) if rules else ([], [])
	for source in target.rglob("*"):
		if source.is_symlink() or not source.is_file():
			continue
		relative = source.relative_to(target)
		if source.is_relative_to(ROOT_PATH) or _matches(relative, exclude):
			continue
		if include and not _matches(relative, include):
			continue
		destination = profile / relative
		destination.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(source, destination)


@click.group()
def cli():
	"""Manage layered configuration profiles."""


@cli.command()
@click.argument("target", type=click.Path(path_type=Path, file_okay=False))
@click.argument("profile", type=click.Path(path_type=Path, exists=True, file_okay=False))
def load(target, profile):
	"""Reset TARGET and load PROFILE."""
	target.mkdir(parents=True, exist_ok=True)
	_apply_profile(target, profile)


@cli.command()
@click.argument("target", type=click.Path(path_type=Path, file_okay=False))
@click.argument("profile", type=click.Path(path_type=Path, exists=True, file_okay=False))
def add(target, profile):
	"""Apply PROFILE on top of the current setup."""
	target.mkdir(parents=True, exist_ok=True)
	_apply_profile(target, profile)


@cli.command()
@click.argument("target", type=click.Path(path_type=Path, file_okay=False))
@click.argument("profile", type=click.Path(path_type=Path, exists=True, file_okay=False))
def remove(target, profile):
	"""Remove PROFILE's managed symlinks from TARGET."""
	_remove_profile_links(target, profile)


@cli.command()
@click.argument("target", type=click.Path(path_type=Path, file_okay=False))
@click.argument("profile", type=click.Path(path_type=Path, exists=True, file_okay=False))
def unload(target, profile):
	"""Unload PROFILE without changing unrelated files."""
	_remove_profile_links(target, profile)


@cli.command()
@click.argument("target", type=click.Path(path_type=Path, file_okay=False))
def reset(target):
	"""Restore TARGET from the default profile."""
	default = PROFILES_PATH / "default"
	if not default.is_dir():
		raise click.ClickException(
			f"no default profile found; run: profiles save {target} {default}"
		)
	for path in target.rglob("*"):
		if path.is_symlink() and path.resolve().is_relative_to(PROFILES_PATH.resolve()):
			path.unlink()
	_apply_profile(target, default)


@cli.command()
@click.option("-r", "rules", type=click.Path(path_type=Path, exists=True), help="Rules file or rules directory.")
@click.argument("target", type=click.Path(path_type=Path, exists=True, file_okay=False))
@click.argument("profile", type=click.Path(path_type=Path, file_okay=False))
def save(rules, target, profile):
	"""Save tracked files from TARGET into PROFILE."""
	_save_profile(target, profile, rules)


@cli.command("backup-to")
@click.option("-r", "rules", is_flag=True, help="Use the default rules file.")
@click.argument("backup", type=click.Path(path_type=Path, file_okay=False))
def backup_to(rules, backup):
	"""Back up the current home directory to BACKUP."""
	rules_path = RULES_PATH if rules else None
	_save_profile(Path.home(), backup, rules_path)


if __name__ == "__main__":
	cli()
