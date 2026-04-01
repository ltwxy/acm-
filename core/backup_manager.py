"""
数据备份与恢复模块
支持自动备份和手动恢复
"""
import sqlite3
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class BackupManager:
    """数据备份管理器"""

    def __init__(self, db_path: Path, backup_dir: Optional[Path] = None):
        self.db_path = db_path
        self.backup_dir = backup_dir or db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, name: Optional[str] = None) -> Dict:
        """
        创建数据库备份

        Args:
            name: 备份名称，不指定则使用时间戳

        Returns:
            备份信息字典
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"backup_{timestamp}"

        backup_path = self.backup_dir / f"{name}.db"
        backup_info_path = self.backup_dir / f"{name}.info.json"

        # 复制数据库
        shutil.copy2(self.db_path, backup_path)

        # 生成备份信息
        info = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "db_path": str(backup_path),
            "db_size": backup_path.stat().st_size,
            "tables": self._get_table_stats(backup_path)
        }

        # 保存备份信息
        with open(backup_info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        # 同时生成一个压缩包
        zip_path = self._create_zip_backup(name, backup_path)

        return {
            **info,
            "zip_path": str(zip_path),
            "success": True
        }

    def _create_zip_backup(self, name: str, db_path: Path) -> Path:
        """创建压缩备份"""
        zip_path = self.backup_dir / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_path, "刷题管理系统.db")
        return zip_path

    def _get_table_stats(self, db_path: Path) -> Dict:
        """获取数据库表统计"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        stats = {}

        tables = [
            'problems', 'platform_problems', 'categories', 'daily_stats',
            'daily_plans', 'task_execution', 'candidate_pool',
            'problem_status_log', 'sync_log'
        ]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except sqlite3.Error:
                stats[table] = 0

        conn.close()
        return stats

    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []

        for info_file in self.backup_dir.glob("*.info.json"):
            try:
                with open(info_file, encoding="utf-8") as f:
                    backups.append(json.load(f))
            except Exception:
                continue

        # 按创建时间倒序
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def restore_backup(self, name: str) -> Dict:
        """
        恢复备份

        Args:
            name: 备份名称（不含扩展名）

        Returns:
            恢复结果
        """
        backup_path = self.backup_dir / f"{name}.db"

        if not backup_path.exists():
            # 尝试从 zip 恢复
            zip_path = self.backup_dir / f"{name}.zip"
            if zip_path.exists():
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(self.backup_dir)
                backup_path = self.backup_dir / "刷题管理系统.db"

        if not backup_path.exists():
            return {
                "success": False,
                "error": f"备份 '{name}' 不存在"
            }

        # 备份当前数据库
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup = self.db_path.parent / f"pre_restore_{timestamp}.db"
        shutil.copy2(self.db_path, current_backup)

        try:
            # 恢复数据库
            shutil.copy2(backup_path, self.db_path)
            return {
                "success": True,
                "message": f"已成功恢复到备份 '{name}'",
                "pre_restore_backup": str(current_backup)
            }
        except Exception as e:
            # 恢复失败，恢复原数据库
            shutil.copy2(current_backup, self.db_path)
            return {
                "success": False,
                "error": f"恢复失败: {str(e)}"
            }

    def delete_backup(self, name: str) -> Dict:
        """删除备份"""
        backup_path = self.backup_dir / f"{name}.db"
        backup_info = self.backup_dir / f"{name}.info.json"
        backup_zip = self.backup_dir / f"{name}.zip"

        deleted = []
        for path in [backup_path, backup_info, backup_zip]:
            if path.exists():
                path.unlink()
                deleted.append(str(path))

        return {
            "success": True,
            "deleted": deleted
        } if deleted else {
            "success": False,
            "error": f"备份 '{name}' 不存在"
        }

    def auto_backup(self, max_backups: int = 10) -> Dict:
        """
        自动备份，保留最近N个备份

        Args:
            max_backups: 最多保留的备份数量

        Returns:
            备份结果
        """
        # 创建新备份
        result = self.create_backup()

        # 清理旧备份
        backups = self.list_backups()
        if len(backups) > max_backups:
            for old_backup in backups[max_backups:]:
                self.delete_backup(old_backup["name"])

        return result
