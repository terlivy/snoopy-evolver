#!/usr/bin/env python3
"""
snoopy-evolver/evolver/solidify.py
固化器 - 将演化建议写入文件并提交 Git

职责：
1. 将基因/演化建议写入文件
2. 创建 Git commit
3. 管理固化历史

参考：evolver-source/src/gep/solidify.js
"""

import json
import os
import subprocess
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
import re


# 路径配置
WORKSPACE_ROOT = Path.home() / ".openclaw" / "workspace"
EVOLUTION_DIR = WORKSPACE_ROOT / "evolutions"
SOLIDIFY_LOG = EVOLUTION_DIR / "solidify_log.jsonl"


@dataclass
class SolidifyResult:
    """固化结果"""
    success: bool
    changes_applied: int = 0
    files_modified: List[str] = None
    commit_hash: Optional[str] = None
    evolution_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        if self.files_modified is None:
            self.files_modified = []

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "changes_applied": self.changes_applied,
            "files_modified": self.files_modified,
            "commit_hash": self.commit_hash,
            "evolution_id": self.evolution_id,
            "message": self.message,
            "error": self.error
        }


@dataclass
class EvolutionSuggestion:
    """演化建议"""
    gene_id: str
    gene_name: str
    signal_type: str
    problem: str
    solution: str
    validation: str
    target_files: List[str] = None
    code_changes: Dict[str, str] = None  # filepath -> new_content
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.target_files is None:
            self.target_files = []
        if self.code_changes is None:
            self.code_changes = {}
        if self.metadata is None:
            self.metadata = {}


class Solidifier:
    """固化器"""

    def __init__(self, evolution_dir: Optional[str] = None):
        if evolution_dir is None:
            evolution_dir = str(EVOLUTION_DIR)
        self.evolution_dir = Path(evolution_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保必要的目录存在"""
        self.evolution_dir.mkdir(parents=True, exist_ok=True)

    def _generate_evolution_id(self) -> str:
        """生成唯一的演化ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{timestamp}_{os.getpid()}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"evo_{timestamp}_{short_hash}"

    def _is_git_repo(self, path: str = None) -> bool:
        """检查是否为 Git 仓库"""
        if path is None:
            path = str(WORKSPACE_ROOT)
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip().lower() == "true"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False

    def _get_git_root(self, path: str = None) -> Optional[str]:
        """获取 Git 仓库根目录"""
        if path is None:
            path = str(WORKSPACE_ROOT)
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None

    def _git_commit(self, message: str, files: List[str] = None) -> Tuple[bool, Optional[str]]:
        """
        创建 Git commit

        Returns:
            (success, commit_hash)
        """
        git_root = self._get_git_root()
        if not git_root:
            return False, None

        try:
            # 添加文件
            if files:
                for f in files:
                    subprocess.run(
                        ["git", "add", f],
                        cwd=git_root,
                        capture_output=True,
                        timeout=10
                    )

            # 创建提交
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # 获取 commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=git_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                commit_hash = hash_result.stdout.strip()[:8]
                return True, commit_hash
            else:
                return False, None

        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, None

    def _write_change(self, filepath: str, content: str) -> bool:
        """写入文件变更"""
        try:
            full_path = Path(filepath)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except IOError as e:
            print(f"[Solidifier] Failed to write {filepath}: {e}")
            return False

    def _apply_code_changes(self, changes: Dict[str, str]) -> Tuple[int, List[str]]:
        """
        应用代码变更

        Args:
            changes: {filepath: new_content}

        Returns:
            (success_count, modified_files)
        """
        success_count = 0
        modified = []

        for filepath, content in changes.items():
            if self._write_change(filepath, content):
                success_count += 1
                modified.append(filepath)

        return success_count, modified

    def _create_evolution_summary(
        self,
        evolution_id: str,
        suggestion: EvolutionSuggestion,
        modified_files: List[str],
        commit_hash: Optional[str] = None
    ) -> Dict:
        """创建演化摘要"""
        return {
            "evolution_id": evolution_id,
            "timestamp": datetime.now().isoformat() + "+08:00",
            "gene_id": suggestion.gene_id,
            "gene_name": suggestion.gene_name,
            "signal_type": suggestion.signal_type,
            "problem": suggestion.problem,
            "solution": suggestion.solution,
            "validation": suggestion.validation,
            "modified_files": modified_files,
            "commit_hash": commit_hash,
            "metadata": suggestion.metadata
        }

    def _log_evolution(self, summary: Dict) -> bool:
        """记录演化历史"""
        try:
            with open(SOLIDIFY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            return True
        except IOError as e:
            print(f"[Solidifier] Failed to log evolution: {e}")
            return False

    def apply_changes(
        self,
        signal_type: str,
        analysis_result: Dict = None,
        dry_run: bool = True
    ) -> SolidifyResult:
        """
        应用演化变更

        Args:
            signal_type: 信号类型
            analysis_result: 分析结果，包含基因和解决方案
            dry_run: 是否为干跑模式

        Returns:
            SolidifyResult
        """
        if analysis_result is None:
            analysis_result = {}

        # 检查是否为 Git 仓库
        is_git = self._is_git_repo()
        if not is_git:
            print(f"[Solidifier] Warning: {WORKSPACE_ROOT} is not a git repo")

        # 生成演化ID
        evolution_id = self._generate_evolution_id()

        # 如果是干跑模式，只记录不实际修改
        if dry_run:
            return SolidifyResult(
                success=True,
                changes_applied=0,
                files_modified=[],
                evolution_id=evolution_id,
                message=f"Dry-run: would apply changes for {signal_type}"
            )

        # 从分析结果构建演化建议
        gene_id = analysis_result.get("gene_id", "unknown")
        gene_name = analysis_result.get("gene_name", "Unknown Gene")

        suggestion = EvolutionSuggestion(
            gene_id=gene_id,
            gene_name=gene_name,
            signal_type=signal_type,
            problem=analysis_result.get("problem", ""),
            solution=analysis_result.get("solution", ""),
            validation=analysis_result.get("validation", ""),
            target_files=analysis_result.get("target_files", []),
            code_changes=analysis_result.get("code_changes", {}),
            metadata=analysis_result.get("metadata", {})
        )

        # 应用代码变更
        modified_files = []
        changes_applied = 0

        if suggestion.code_changes:
            changes_applied, modified_files = self._apply_code_changes(
                suggestion.code_changes
            )

        # 创建 Git 提交（如果有文件变更）
        commit_hash = None
        if modified_files and is_git:
            commit_message = f"Evolution: {gene_name} for {signal_type}\n\n"
            commit_message += f"Gene: {gene_id}\n"
            commit_message += f"Problem: {suggestion.problem[:100]}\n"
            commit_message += f"Evolution ID: {evolution_id}"

            success, commit_hash = self._git_commit(commit_message, modified_files)
            if not success:
                print(f"[Solidifier] Warning: git commit failed")
                commit_hash = None

        # 记录演化历史
        summary = self._create_evolution_summary(
            evolution_id, suggestion, modified_files, commit_hash
        )
        self._log_evolution(summary)

        return SolidifyResult(
            success=True,
            changes_applied=changes_applied,
            files_modified=modified_files,
            commit_hash=commit_hash,
            evolution_id=evolution_id,
            message=f"Applied {changes_applied} changes for {signal_type}"
        )

    def apply_gene(self, gene: Dict, dry_run: bool = True) -> SolidifyResult:
        """
        应用基因建议

        Args:
            gene: 基因数据，包含 solution, target_files 等
            dry_run: 是否为干跑模式

        Returns:
            SolidifyResult
        """
        signal_type = gene.get("source_signal", gene.get("gene_id", "unknown"))

        analysis_result = {
            "gene_id": gene.get("gene_id"),
            "gene_name": gene.get("name"),
            "problem": gene.get("problem", ""),
            "solution": gene.get("solution", ""),
            "validation": gene.get("validation", ""),
            "target_files": gene.get("target_files", []),
            "code_changes": gene.get("code_changes", {}),
            "metadata": gene.get("metadata", {})
        }

        return self.apply_changes(signal_type, analysis_result, dry_run)

    def get_evolution_history(self, limit: int = 20) -> List[Dict]:
        """获取演化历史"""
        evolutions = []

        if not SOLIDIFY_LOG.exists():
            return evolutions

        try:
            with open(SOLIDIFY_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        evolutions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass

        return evolutions[-limit:] if len(evolutions) > limit else evolutions

    def rollback_evolution(self, evolution_id: str) -> SolidifyResult:
        """
        回滚指定演化

        Args:
            evolution_id: 演化ID

        Returns:
            SolidifyResult
        """
        # 查找对应的演化记录
        evolutions = self.get_evolution_history(limit=1000)

        target = None
        for evo in evolutions:
            if evo.get("evolution_id") == evolution_id:
                target = evo
                break

        if not target:
            return SolidifyResult(
                success=False,
                error=f"Evolution {evolution_id} not found"
            )

        # 获取修改的文件
        modified_files = target.get("modified_files", [])

        if not modified_files:
            return SolidifyResult(
                success=True,
                message=f"No files to rollback for {evolution_id}"
            )

        # 检查是否为 Git 仓库
        if not self._is_git_repo():
            return SolidifyResult(
                success=False,
                error="Not a git repo, cannot rollback"
            )

        # 使用 git checkout 恢复文件
        git_root = self._get_git_root()
        if not git_root:
            return SolidifyResult(
                success=False,
                error="Cannot find git root"
            )

        try:
            # 获取当前提交的前一个提交
            result = subprocess.run(
                ["git", "log", "--oneline", "-2"],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0 or len(result.stdout.strip().split("\n")) < 2:
                return SolidifyResult(
                    success=False,
                    error="Not enough commits to rollback"
                )

            # 恢复到上一个提交
            for filepath in modified_files:
                subprocess.run(
                    ["git", "checkout", "HEAD~1", "--", filepath],
                    cwd=git_root,
                    capture_output=True,
                    timeout=10
                )

            # 创建回滚提交
            rollback_message = f"Rollback: {evolution_id}\n\n"
            rollback_message += f"Reverted changes from {target.get('gene_name', 'unknown')}"

            success, commit_hash = self._git_commit(rollback_message, modified_files)

            return SolidifyResult(
                success=success,
                changes_applied=len(modified_files),
                files_modified=modified_files,
                commit_hash=commit_hash if success else None,
                evolution_id=evolution_id,
                message=f"Rolled back {len(modified_files)} files"
            )

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            return SolidifyResult(
                success=False,
                error=f"Rollback failed: {str(e)}"
            )


# ============================================================================
# 便捷函数
# ============================================================================

_solidifier_instance = None


def get_solidifier() -> Solidifier:
    """获取固化器单例"""
    global _solidifier_instance
    if _solidifier_instance is None:
        _solidifier_instance = Solidifier()
    return _solidifier_instance


def apply_changes(signal_type: str, analysis_result: Dict = None, dry_run: bool = True) -> SolidifyResult:
    """
    应用变更的便捷函数

    Args:
        signal_type: 信号类型
        analysis_result: 分析结果
        dry_run: 是否干跑

    Returns:
        SolidifyResult
    """
    return get_solidifier().apply_changes(signal_type, analysis_result, dry_run)


def apply_gene(gene: Dict, dry_run: bool = True) -> SolidifyResult:
    """应用基因的便捷函数"""
    return get_solidifier().apply_gene(gene, dry_run)


def get_evolution_history(limit: int = 20) -> List[Dict]:
    """获取演化历史"""
    return get_solidifier().get_evolution_history(limit)


if __name__ == "__main__":
    print("=== Solidify 测试 ===")

    solidifier = Solidifier()

    # 测试1：干跑模式
    print("\n[干跑测试]")
    result = solidifier.apply_changes(
        "test_signal",
        {
            "gene_id": "test_gene",
            "gene_name": "测试基因",
            "problem": "测试问题",
            "solution": "测试解决方案"
        },
        dry_run=True
    )
    print(f"  结果: {result.message}")
    print(f"  演化ID: {result.evolution_id}")

    # 测试2：Git 状态检查
    print(f"\n[Git 状态]")
    is_git = solidifier._is_git_repo()
    print(f"  是 Git 仓库: {is_git}")
    if is_git:
        git_root = solidifier._get_git_root()
        print(f"  Git 根目录: {git_root}")

    # 测试3：演化历史
    print("\n[演化历史]")
    history = solidifier.get_evolution_history(limit=5)
    print(f"  最近演化数: {len(history)}")

    print("\n=== 测试完成 ===")
