#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment Reconciliation System - Core Module
Adapted from reconcile-payment Skill for cloud deployment
"""

import os
import json
import csv
import chardet
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# Default config path (relative to this file)
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    config_path = config_path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return get_default_config()
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_default_config() -> Dict[str, Any]:
    """Return default configuration"""
    return {
        "game_suppliers": {
            "suppliers": [
                {
                    "name": "RED",
                    "order_id_column": "订单编号",
                    "channel_column": "支付渠道",
                    "status_column": "状态",
                    "amount_column": "实际金额",
                    "currency_unit": "个位"
                }
            ]
        },
        "channel_configs": {},
        "encoding": {
            "default": "utf-8",
            "try_order": ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030", "latin1"],
            "fallback": True
        },
        "delimiter": {
            "try_order": [",", "\t", ";", "|"]
        },
        "output": {
            "amount_format": "¥{:.2f}",
            "show_details": True
        }
    }


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize config to use consistent internal keys"""
    normalized = {}

    # Handle supplier config - support both Chinese and English keys
    if "game_suppliers" in config:
        normalized["game_suppliers"] = config["game_suppliers"]
    elif "游戏供应商配置" in config:
        suppliers = config["游戏供应商配置"]
        normalized["game_suppliers"] = {
            "suppliers": suppliers.get("供应商列表", suppliers.get("suppliers", []))
        }

    # Handle channel configs
    if "channel_configs" in config:
        normalized["channel_configs"] = config["channel_configs"]
    elif "渠道配置" in config:
        normalized["channel_configs"] = config["渠道配置"]

    # Handle encoding config
    if "encoding" in config:
        normalized["encoding"] = config["encoding"]
    elif "编码配置" in config:
        enc_config = config["编码配置"]
        normalized["encoding"] = {
            "default": enc_config.get("默认编码", enc_config.get("default", "utf-8")),
            "try_order": enc_config.get("尝试编码顺序", enc_config.get("try_order", ["utf-8"])),
            "fallback": enc_config.get("容错模式", enc_config.get("fallback", True))
        }

    # Handle delimiter config
    if "delimiter" in config:
        normalized["delimiter"] = config["delimiter"]
    elif "分隔符配置" in config:
        delim_config = config["分隔符配置"]
        normalized["delimiter"] = {
            "try_order": delim_config.get("尝试顺序", delim_config.get("try_order", [",", "\t", ";", "|"]))
        }

    # Handle output config
    if "output" in config:
        normalized["output"] = config["output"]
    elif "输出配置" in config:
        out_config = config["输出配置"]
        normalized["output"] = {
            "amount_format": out_config.get("金额格式", out_config.get("amount_format", "¥{:.2f}")),
            "show_details": out_config.get("显示详情", out_config.get("show_details", True))
        }

    # Add fallback for missing keys
    if "game_suppliers" not in normalized:
        normalized["game_suppliers"] = {"suppliers": []}
    if "channel_configs" not in normalized:
        normalized["channel_configs"] = {}
    if "encoding" not in normalized:
        normalized["encoding"] = {"default": "utf-8", "try_order": ["utf-8"]}
    if "delimiter" not in normalized:
        normalized["delimiter"] = {"try_order": [",", "\t", ";", "|"]}
    if "output" not in normalized:
        normalized["output"] = {"amount_format": "¥{:.2f}"}

    return normalized


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet"""
    with open(file_path, "rb") as f:
        raw = f.read(10000)
    result = chardet.detect(raw)
    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)

    if confidence < 0.7:
        config = normalize_config(load_config())
        for enc in config.get("encoding", {}).get("try_order", ["utf-8"]):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    f.read(1000)
                return enc
            except (UnicodeDecodeError, LookupError):
                continue
    return encoding


def detect_delimiter(file_path: str, encoding: str) -> str:
    """Detect CSV delimiter"""
    config = normalize_config(load_config())
    delimiters = config.get("delimiter", {}).get("try_order", [",", "\t", ";", "|"])

    with open(file_path, "r", encoding=encoding, newline="") as f:
        sample = f.read(1024)

    for delim in delimiters:
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(delimiters))
            return dialect.delimiter
        except csv.Error:
            continue
    return ","


def read_file_safe(file_path: str) -> Optional[pd.DataFrame]:
    """Safely read file, trying multiple formats (Excel, CSV)"""
    file_path = str(file_path)

    if not Path(file_path).exists():
        print(f"[ERROR] File not found: {file_path}")
        return None

    # First try: Excel format
    # Try header_row=0 first (most common), then fallback to 1, then None
    for header_row in [0, 1, None]:
        try:
            df = pd.read_excel(file_path, engine="openpyxl", header=header_row)
            if len(df.columns) > 1:
                first_col = str(df.columns[0])
                # Valid headers should not look like data (e.g., "D001", "001")
                # Reject if first column is:
                # - A number (all digits)
                # - Starts with letter followed by digits (likely an ID like "D001", "R123")
                # - Starts with "Unnamed"
                import re
                if (not first_col.startswith("Unnamed") and
                    not first_col.isdigit() and
                    not re.match(r'^[A-Za-z]+\d+$', first_col)):
                    return df
        except Exception:
            continue

    # If Excel failed, try CSV
    encoding = detect_encoding(file_path)
    delimiter = detect_delimiter(file_path, encoding)

    try:
        return pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV {file_path} (encoding: {encoding}, delimiter: {repr(delimiter)}): {e}")
        try:
            return pd.read_csv(file_path, encoding="latin1", delimiter=delimiter, on_bad_lines="skip")
        except Exception as e2:
            print(f"[ERROR] Fallback also failed: {e2}")
            return None


def clean_amount(value: Any) -> float:
    """Clean and convert amount to float"""
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("CNY", "").replace("$", "").replace(",", "").replace("¥", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def normalize_str(value: Any) -> str:
    """Normalize value to string"""
    if pd.isna(value):
        return ""
    return str(value).strip()


class Reconciler:
    """Main reconciliation class"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        raw_config = config or load_config()
        self.config = normalize_config(raw_config)
        self.game_deposit_df: Optional[pd.DataFrame] = None
        self.game_withdraw_df: Optional[pd.DataFrame] = None
        self.channel_dfs: Dict[str, pd.DataFrame] = {}
        self.results: Dict[str, Any] = {}

    def load_game_deposit(self, file_path: str, supplier_name: str = "RED") -> bool:
        """Load game deposit file"""
        df = read_file_safe(file_path)
        if df is None:
            return False

        supplier = self._get_supplier_config(supplier_name) or {}
        df.columns = df.columns.astype(str).str.strip()

        status_col = supplier.get("status_column", "状态")
        status_value = "成功"

        if status_col in df.columns:
            df = df[df[status_col].astype(str).str.strip() == status_value].copy()

        self.game_deposit_df = df
        return True

    def load_game_withdraw(self, file_path: str, supplier_name: str = "RED") -> bool:
        """Load game withdraw file"""
        df = read_file_safe(file_path)
        if df is None:
            return False

        supplier = self._get_supplier_config(supplier_name) or {}
        df.columns = df.columns.astype(str).str.strip()

        status_col = supplier.get("status_column", "状态")
        status_value = "成功"

        if status_col in df.columns:
            df = df[df[status_col].astype(str).str.strip() == status_value].copy()

        self.game_withdraw_df = df
        return True

    def load_channel_file(self, file_path: str, channel_name: str) -> bool:
        """Load payment channel file"""
        df = read_file_safe(file_path)
        if df is None:
            return False

        df.columns = df.columns.astype(str).str.strip()
        self.channel_dfs[channel_name] = df
        return True

    def _get_supplier_config(self, supplier_name: str) -> Optional[Dict[str, Any]]:
        """Get supplier configuration"""
        suppliers = self.config.get("game_suppliers", {}).get("suppliers", [])
        for s in suppliers:
            if s.get("name") == supplier_name:
                return s
        return None

    def _get_channel_config(self, channel_name: str) -> Dict[str, Any]:
        """Get channel configuration"""
        channel_configs = self.config.get("channel_configs", {})
        if channel_name in channel_configs:
            return channel_configs[channel_name]
        for key, value in channel_configs.items():
            if key.lower() == channel_name.lower():
                return value
        return {
            "channel_table_config": {
                "field_map": {},
                "success_values": ["成功", "success", "1", "completed"]
            }
        }

    def reconcile(self, supplier_name: str = "RED") -> Dict[str, Any]:
        """Perform reconciliation"""
        if self.game_deposit_df is None and self.game_withdraw_df is None:
            return {"error": "Please load game backend files first"}

        results = {
            "summary": {
                "total_deposit": {"count": 0, "matched": 0, "amount": 0, "matched_amount": 0},
                "total_withdraw": {"count": 0, "matched": 0, "amount": 0, "matched_amount": 0}
            },
            "channels": {},
            "mismatched": [],
            "missing_in_channel": [],
            "missing_in_game": []
        }

        supplier = self._get_supplier_config(supplier_name) or {}
        order_id_col = supplier.get("order_id_column", "订单编号")
        channel_col = supplier.get("channel_column", "支付渠道")
        amount_col = supplier.get("amount_column", "实际金额")

        # Get all channels
        all_channels = set()
        if self.game_deposit_df is not None and channel_col in self.game_deposit_df.columns:
            all_channels.update(self.game_deposit_df[channel_col].dropna().unique())
        if self.game_withdraw_df is not None and channel_col in self.game_withdraw_df.columns:
            all_channels.update(self.game_withdraw_df[channel_col].dropna().unique())

        for channel_name in all_channels:
            channel = normalize_str(channel_name)
            if not channel or channel == "nan":
                continue

            # Find matching channel file
            channel_df = None
            actual_channel_name = None
            for file_channel, df in self.channel_dfs.items():
                if file_channel.lower() in channel.lower() or channel.lower() in file_channel.lower():
                    channel_df = df
                    actual_channel_name = file_channel
                    break

            if channel_df is None:
                continue

            channel_config = self._get_channel_config(channel)
            channel_result = self._reconcile_channel(
                channel, channel_df, channel_config, order_id_col, amount_col
            )
            results["channels"][channel] = channel_result

            for key in ["count", "matched", "amount", "matched_amount"]:
                results["summary"]["total_deposit"][key] += channel_result.get("deposit", {}).get(key, 0)
                results["summary"]["total_withdraw"][key] += channel_result.get("withdraw", {}).get(key, 0)

            results["mismatched"].extend([
                {**p, "channel": channel, "type": "deposit"} for p in channel_result.get("deposit_problems", [])
            ])
            results["missing_in_channel"].extend([
                {**p, "channel": channel, "type": "deposit"} for p in channel_result.get("deposit_missing", [])
            ])
            results["missing_in_game"].extend([
                {**p, "channel": channel, "type": "withdraw"} for p in channel_result.get("withdraw_missing", [])
            ])

        self.results = results
        return results

    def _reconcile_channel(
        self,
        channel_name: str,
        channel_df: pd.DataFrame,
        channel_config: Dict[str, Any],
        order_id_col: str,
        amount_col: str
    ) -> Dict[str, Any]:
        """Reconcile a single channel"""
        result = {
            "deposit": {"count": 0, "matched": 0, "amount": 0, "matched_amount": 0},
            "withdraw": {"count": 0, "matched": 0, "amount": 0, "matched_amount": 0},
            "deposit_problems": [],
            "withdraw_problems": [],
            "deposit_missing": [],
            "withdraw_missing": []
        }

        # Get channel config mapping - support both old and new format
        channel_table_config = channel_config.get("渠道表配置", {})
        if not channel_table_config:
            channel_table_config = channel_config.get("channel_table_config", {})

        channel_field_map = channel_table_config.get("字段映射", channel_table_config.get("field_map", {}))
        channel_order_col = channel_field_map.get("平台订单号", channel_field_map.get("商户订单号", "商户订单号"))
        channel_amount_col = channel_field_map.get("金额", "金额")

        # Build channel orders dict
        channel_orders = {}
        for _, row in channel_df.iterrows():
            order_id = normalize_str(row.get(channel_order_col, ""))
            amount = clean_amount(row.get(channel_amount_col, 0))
            if order_id:
                channel_orders[order_id] = amount

        # Reconcile deposits
        if self.game_deposit_df is not None:
            deposit_df = self._filter_by_channel(self.game_deposit_df, channel_name)
            for _, row in deposit_df.iterrows():
                result["deposit"]["count"] += 1
                order_id = normalize_str(row.get(order_id_col, ""))
                amount = clean_amount(row.get(amount_col, 0))
                result["deposit"]["amount"] += amount

                if order_id in channel_orders:
                    channel_amount = channel_orders.pop(order_id)  # Remove to track missing in game
                    tolerance = max(0.01, amount * 0.01)
                    if abs(amount - channel_amount) <= tolerance:
                        result["deposit"]["matched"] += 1
                        result["deposit"]["matched_amount"] += amount
                    else:
                        result["deposit_problems"].append({
                            "order_id": order_id,
                            "game_amount": amount,
                            "channel_amount": channel_amount
                        })
                else:
                    result["deposit_missing"].append({
                        "order_id": order_id,
                        "game_amount": amount
                    })

        # Reconcile withdraws
        if self.game_withdraw_df is not None:
            withdraw_df = self._filter_by_channel(self.game_withdraw_df, channel_name)
            for _, row in withdraw_df.iterrows():
                result["withdraw"]["count"] += 1
                order_id = normalize_str(row.get(order_id_col, ""))
                amount = clean_amount(row.get(amount_col, 0))
                result["withdraw"]["amount"] += amount

                if order_id in channel_orders:
                    channel_amount = channel_orders.pop(order_id)
                    tolerance = max(0.01, amount * 0.01)
                    if abs(amount - channel_amount) <= tolerance:
                        result["withdraw"]["matched"] += 1
                        result["withdraw"]["matched_amount"] += amount
                    else:
                        result["withdraw_problems"].append({
                            "order_id": order_id,
                            "game_amount": amount,
                            "channel_amount": channel_amount
                        })
                else:
                    result["withdraw_missing"].append({
                        "order_id": order_id,
                        "game_amount": amount
                    })

        # Remaining in channel_orders are missing in game
        for order_id, amount in channel_orders.items():
            result["withdraw_missing"].append({
                "order_id": order_id,
                "channel_amount": amount,
                "note": "only in channel file"
            })

        return result

    def _filter_by_channel(self, df: pd.DataFrame, channel_name: str) -> pd.DataFrame:
        """Filter dataframe by channel name"""
        supplier = self._get_supplier_config("RED") or {}
        channel_col = supplier.get("channel_column", "支付渠道")
        if channel_col in df.columns:
            return df[df[channel_col].astype(str).str.strip() == channel_name].copy()
        return df


def run_reconcile_sync(
    deposit_path: str,
    withdraw_path: str,
    channel_paths: Dict[str, str],
    supplier_name: str = "RED",
    config_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entry point for synchronous reconciliation execution

    Args:
        deposit_path: Path to deposit file
        withdraw_path: Path to withdraw file
        channel_paths: Dictionary of {channel_name: file_path}
        supplier_name: Game supplier name
        config_override: Optional config override (for LLM adaptation)

    Returns:
        Reconciliation results dictionary with:
        - summary: Overall statistics
        - channels: Per-channel breakdown
        - mismatched: Orders with amount mismatch
        - missing_in_channel: Orders in game but not in channel
        - missing_in_game: Orders in channel but not in game
    """
    config = load_config()
    if config_override:
        # Apply config override for dynamic field mapping
        config = apply_config_override(config, config_override)

    reconciler = Reconciler(config)

    # Load files
    if deposit_path and Path(deposit_path).exists():
        if not reconciler.load_game_deposit(deposit_path, supplier_name):
            return {"error": f"Failed to load deposit file: {deposit_path}"}

    if withdraw_path and Path(withdraw_path).exists():
        if not reconciler.load_game_withdraw(withdraw_path, supplier_name):
            return {"error": f"Failed to load withdraw file: {withdraw_path}"}

    for channel_name, channel_path in channel_paths.items():
        if not reconciler.load_channel_file(channel_path, channel_name):
            return {"error": f"Failed to load channel file: {channel_path}"}

    # Perform reconciliation
    results = reconciler.reconcile(supplier_name)
    return results


def apply_config_override(
    base_config: Dict[str, Any],
    override: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply LLM-generated config override to base config"""
    import copy
    merged = copy.deepcopy(base_config)

    # Apply field mapping overrides
    if "field_mapping" in override:
        field_mapping = override["field_mapping"]

        # Update supplier columns
        if "deposit" in field_mapping:
            if "game_suppliers" not in merged:
                merged["game_suppliers"] = {"suppliers": []}
            for supplier in merged["game_suppliers"].get("suppliers", []):
                supplier.update(field_mapping["deposit"])

        # Update channel field mappings
        if "channels" in field_mapping:
            if "channel_configs" not in merged:
                merged["channel_configs"] = {}
            for channel_name, mapping in field_mapping["channels"].items():
                if channel_name not in merged["channel_configs"]:
                    merged["channel_configs"][channel_name] = {}
                if "channel_table_config" not in merged["channel_configs"][channel_name]:
                    merged["channel_configs"][channel_name]["channel_table_config"] = {}
                merged["channel_configs"][channel_name]["channel_table_config"]["field_map"] = mapping

    return merged
