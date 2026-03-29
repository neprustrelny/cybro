#!/usr/bin/env python3
"""
🔷 CYBRO WatchDog v7.0 - ULTIMATE CYBER SECURITY SUITE
„BOH MEDZI HACKERMI“ - Komplexný bezpečnostný nástroj pre profesionálov
Integruje všetky pokročilé funkcie: anonymizácia, sieťová analýza, AI, pentesting, BLE, reporting a viac
Autor: CYBRO & Johnny WatchDog (Ultimate Edition)
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
import re
import subprocess
import threading
from pathlib import Path
import asyncio
import platform
import binascii
import json
import time
import math
import random
import traceback
from datetime import datetime, timedelta, timezone
import uuid
import sqlite3
import hashlib
import base64
import csv
import ipaddress
import signal
import wave
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import webbrowser
import logging

# Voliteľné importy
try:
    import pytesseract
    from PIL import Image, ImageTk, ImageGrab
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import bleak
    from bleak import BleakScanner, BleakClient
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

try:
    import xml.etree.ElementTree as ET
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP, ICMP
    from scapy.layers.l2 import ARP, Ether
    from scapy.layers.http import HTTPRequest
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Passive monitoring modules
try:
    from passive_capture import PassiveCapture
    from device_registry import DeviceRegistry, OUIResolver
    from event_engine import EventEngine, DeviceEventType
    from storage import DeviceStorage
    PASSIVE_MODULES_AVAILABLE = True
except Exception as passive_exc:
    PASSIVE_MODULES_AVAILABLE = False
    passive_import_error = passive_exc

# Local AI analyst modules
local_ai_error = None
try:
    from ai_context import build_context as build_ai_context, build_prompt as build_ai_prompt
    from ai_engine import analyze_event as ai_analyze_event, is_model_available as ai_model_available
    from ai_insights import normalize_insight
    LOCAL_AI_AVAILABLE = ai_model_available()
    if not LOCAL_AI_AVAILABLE:
        local_ai_error = "marek-ai:latest not found or Ollama unavailable"
except Exception as local_ai_exc:
    LOCAL_AI_AVAILABLE = False
    local_ai_error = local_ai_exc
    build_ai_context = None  # type: ignore
    build_ai_prompt = None  # type: ignore
    ai_analyze_event = None  # type: ignore
    normalize_insight = None  # type: ignore

embedded_ai_chat_error = None
try:
    from ai_backend import get_backend
    from data_access import (
        list_recent_artifacts,
        list_reports,
        read_text_file,
        sqlite_table_overview,
        tail_text_file,
        validate_artifact_path,
    )
    EMBEDDED_AI_CHAT_AVAILABLE = True
except Exception as embedded_ai_exc:
    EMBEDDED_AI_CHAT_AVAILABLE = False
    embedded_ai_chat_error = embedded_ai_exc
    get_backend = None  # type: ignore
    list_recent_artifacts = None  # type: ignore
    list_reports = None  # type: ignore
    read_text_file = None  # type: ignore
    sqlite_table_overview = None  # type: ignore
    tail_text_file = None  # type: ignore
    validate_artifact_path = None  # type: ignore

# Konštanty a priečinky
PROJECT_ROOT = Path(__file__).resolve().parent
PRIMARY_LOG_DIR = PROJECT_ROOT / "cybro_logs"
FALLBACK_RUNTIME_ROOT = Path.home() / ".cache" / "cybro"


def _resolve_runtime_root() -> Path:
    try:
        PRIMARY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if PRIMARY_LOG_DIR.is_dir() and os.access(PRIMARY_LOG_DIR, os.W_OK):
        return PROJECT_ROOT

    FALLBACK_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    return FALLBACK_RUNTIME_ROOT


RUNTIME_ROOT = _resolve_runtime_root()
RUNTIME_FALLBACK_USED = RUNTIME_ROOT != PROJECT_ROOT

if RUNTIME_FALLBACK_USED:
    LOG_DIR = RUNTIME_ROOT / "cybro_logs"
    ASSET_DIR = RUNTIME_ROOT / "cybro_assets"
    CORRUPTED_DIR = RUNTIME_ROOT / "corrupted_data"
    CAPTURE_DIR = RUNTIME_ROOT / "packet_captures"
    REPORTS_DIR = RUNTIME_ROOT / "security_reports"
    DB_PATH = RUNTIME_ROOT / "cybro_watchdog.db"
    CONFIG_PATH = RUNTIME_ROOT / "cybro_config.json"
else:
    LOG_DIR = PRIMARY_LOG_DIR
    ASSET_DIR = PROJECT_ROOT / "cybro_assets"
    CORRUPTED_DIR = PROJECT_ROOT / "corrupted_data"
    CAPTURE_DIR = PROJECT_ROOT / "packet_captures"
    REPORTS_DIR = PROJECT_ROOT / "security_reports"
    DB_PATH = PROJECT_ROOT / "cybro_watchdog.db"
    CONFIG_PATH = PROJECT_ROOT / "cybro_config.json"

PROFILE_DIR = LOG_DIR / "network_profiles"

for d in [LOG_DIR, PROFILE_DIR, ASSET_DIR, CORRUPTED_DIR, CAPTURE_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "cybro.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")]
)
logger = logging.getLogger("CYBRO")

AI_CHAT_SYSTEM_PROMPT = (
    "Si CYBRO AI Analyst. Owner mode: all devices/networks are owned and authorized. "
    "Odpovedaj krokovo k cielu: diagnostika -> zistenie IP -> test -> pristup. "
    "MAC adresa nie je IP adresa a nikdy ich nezamen. "
    "Ak chyba IP pre danu MAC, povedz presne co doplnit: Add IPs from DB / ip neigh / local snapshot. "
    "Pracuj iba s poskytnutym CYBRO kontextom a nehalucinuj."
)
AI_CHAT_MAX_CONTEXT_CHARS = 50_000
AI_CHAT_MAX_HISTORY_MESSAGES = 12
AI_CHAT_PRIMARY_AUDIT_LOG = PROJECT_ROOT / "cybro_logs" / "ai_chat_audit.log"
AI_CHAT_FALLBACK_AUDIT_LOG = Path.home() / ".cache" / "cybro" / "ai_chat_audit.log"


def _resolve_ai_chat_audit_log() -> tuple[Path, bool]:
    try:
        AI_CHAT_PRIMARY_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if AI_CHAT_PRIMARY_AUDIT_LOG.parent.is_dir() and os.access(AI_CHAT_PRIMARY_AUDIT_LOG.parent, os.W_OK):
        return AI_CHAT_PRIMARY_AUDIT_LOG, False

    AI_CHAT_FALLBACK_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    return AI_CHAT_FALLBACK_AUDIT_LOG, True


AI_CHAT_AUDIT_LOG, AI_CHAT_AUDIT_FALLBACK_USED = _resolve_ai_chat_audit_log()


def _append_ai_chat_audit(action: str, files_read, note: str = "") -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "files_read": [{"path": path, "bytes": size} for path, size in files_read],
        "note": note,
    }
    try:
        AI_CHAT_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AI_CHAT_AUDIT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass

class UltimateNotificationSystem:
    def __init__(self, parent):
        self.parent = parent
        self.notifications = []
        self.alert_levels = {
            'info': '#2196F3',
            'warning': '#FF9800', 
            'critical': '#F44336',
            'success': '#4CAF50',
            'hacker': '#9C27B0'
        }
        self.create_notification_area()
    
    def create_notification_area(self):
        """Vytvorí oblast pre notifikácie"""
        self.notification_frame = tk.Frame(
            self.parent.root,
            bg=self.parent.colors['surface'],
            width=400,
            height=300
        )
        self.notification_frame.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)
        self.notification_frame.pack_propagate(False)
        
        # Header
        header = tk.Frame(self.notification_frame, bg=self.parent.colors['primary'])
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text="🔔 CYBRO ALERTS",
            font=("Courier New", 10, "bold"),
            bg=self.parent.colors['primary'],
            fg='white'
        ).pack(pady=5)
        
        # Scrollable content
        self.notification_canvas = tk.Canvas(
            self.notification_frame, 
            bg=self.parent.colors['surface'],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(self.notification_frame, orient="vertical", command=self.notification_canvas.yview)
        self.scrollable_frame = tk.Frame(self.notification_canvas, bg=self.parent.colors['surface'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.notification_canvas.configure(scrollregion=self.notification_canvas.bbox("all"))
        )
        
        self.notification_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.notification_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.notification_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def add_notification(self, title, message, level='info', timeout=8000):
        """Pridá notifikáciu do systému"""
        notification_id = str(uuid.uuid4())[:8]
        notification = {
            'id': notification_id,
            'title': title,
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'timeout': timeout
        }
        self.notifications.append(notification)
        self._show_notification(notification)
    
    def _show_notification(self, notification):
        """Zobrazí notifikáciu v GUI"""
        def create_notification():
            frame = tk.Frame(
                self.scrollable_frame,
                bg=self.alert_levels[notification['level']],
                relief='raised',
                bd=1,
                width=380
            )
            frame.pack(fill=tk.X, padx=5, pady=2)
            frame.pack_propagate(False)
            
            # Header
            header = tk.Frame(frame, bg=self.alert_levels[notification['level']])
            header.pack(fill=tk.X, padx=5, pady=2)
            
            tk.Label(
                header,
                text=f"🔔 {notification['title']}",
                font=("Courier New", 9, "bold"),
                bg=self.alert_levels[notification['level']],
                fg='white',
                anchor='w'
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(
                header,
                text=notification['timestamp'],
                font=("Courier New", 8),
                bg=self.alert_levels[notification['level']],
                fg='white'
            ).pack(side=tk.RIGHT)
            
            # Message
            message_frame = tk.Frame(frame, bg='#1a1a2e')
            message_frame.pack(fill=tk.X, padx=2, pady=2)
            
            tk.Label(
                message_frame,
                text=notification['message'],
                font=("Courier New", 8),
                bg='#1a1a2e',
                fg='white',
                wraplength=370,
                justify=tk.LEFT
            ).pack(fill=tk.X, padx=5, pady=5)
            
            # Auto-remove after timeout
            def remove():
                if frame.winfo_exists():
                    frame.destroy()
            
            self.parent.root.after(notification['timeout'], remove)
        
        self.parent.root.after(0, create_notification)

class UltimateAnonymizer:
    def __init__(self, parent):
        self.parent = parent
        self.patterns = {
            'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phones': r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            'ips': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'macs': r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
            'credit_cards': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'iban': r'[A-Z]{2}\d{2}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{0,20}',
            'btc': r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}',
            'coordinates': r'[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)\s*[-+,]?\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)'
        }
        
        self.custom_patterns = []
        self.anonymization_history = []
    
    def setup_ui(self, parent):
        """Nastaví UI pre anonymizér"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="🎭 ULTIMATE ANONYMIZER - TOTAL DATA PROTECTION",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        # Main container
        main_container = tk.Frame(parent, bg=self.parent.colors['background'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left panel - Input
        left_panel = tk.Frame(main_container, bg=self.parent.colors['surface'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(
            left_panel,
            text="INPUT DATA:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        self.input_text = scrolledtext.ScrolledText(
            left_panel,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg='#1a1a1a',
            fg='white',
            height=20
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right panel - Output
        right_panel = tk.Frame(main_container, bg=self.parent.colors['surface'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(
            right_panel,
            text="ANONYMIZED OUTPUT:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        self.output_text = scrolledtext.ScrolledText(
            right_panel,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg='#1a1a1a',
            fg='#00ff00',
            height=20
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_panel = tk.Frame(parent, bg=self.parent.colors['surface'])
        control_panel.pack(fill=tk.X, padx=20, pady=10)
        
        # Anonymization buttons
        anonym_buttons = [
            ("🔍 QUICK SCAN", self.quick_scan),
            ("🛡️ DEEP ANONYMIZE", self.deep_anonymize),
            ("🎯 CUSTOM PATTERNS", self.manage_patterns),
            ("📊 STATISTICS", self.show_statistics),
            ("💾 BATCH PROCESS", self.batch_process)
        ]
        
        for i, (text, command) in enumerate(anonym_buttons):
            btn = tk.Button(
                control_panel,
                text=text,
                command=command,
                font=("Courier New", 9, "bold"),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=15,
                pady=8
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
        
        # File operations
        file_buttons = [
            ("📁 LOAD FILE", self.load_file),
            ("💾 SAVE OUTPUT", self.save_output),
            ("📋 EXPORT REPORT", self.export_report),
            ("🧹 CLEAR ALL", self.clear_all)
        ]
        
        for i, (text, command) in enumerate(file_buttons):
            btn = tk.Button(
                control_panel,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.parent.colors['accent'],
                fg='white',
                relief='flat',
                padx=15,
                pady=8
            )
            btn.grid(row=1, column=i, padx=5, pady=5)
        
        control_panel.columnconfigure("all", weight=1)
    
    def quick_scan(self):
        """Rýchle skenovanie citlivých údajov"""
        text = self.input_text.get(1.0, tk.END)
        if not text.strip():
            self.parent.notification_system.add_notification(
                "Empty Input", 
                "Please enter text to analyze",
                'warning'
            )
            return
        
        def scan():
            try:
                stats = {}
                for pattern_name, pattern in self.patterns.items():
                    matches = re.findall(pattern, text)
                    if matches:
                        stats[pattern_name] = len(matches)
                
                # Add custom patterns
                for custom_name, custom_pattern in self.custom_patterns:
                    matches = re.findall(custom_pattern, text)
                    if matches:
                        stats[custom_name] = len(matches)
                
                # Show results
                result_text = "🔍 QUICK SCAN RESULTS:\n" + "="*40 + "\n"
                if stats:
                    for data_type, count in stats.items():
                        result_text += f"📊 {data_type.upper()}: {count} found\n"
                else:
                    result_text += "✅ No sensitive data detected\n"
                
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(1.0, result_text)
                
                self.parent.notification_system.add_notification(
                    "Scan Complete",
                    f"Found {sum(stats.values())} sensitive items",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=scan, daemon=True).start()
    
    def deep_anonymize(self):
        """Hĺbková anonymizácia"""
        text = self.input_text.get(1.0, tk.END)
        if not text.strip():
            self.parent.notification_system.add_notification(
                "Empty Input", 
                "Please enter text to anonymize",
                'warning'
            )
            return
        
        def anonymize():
            try:
                anonymized = text
                replacement_map = {}
                stats = {}
                
                for pattern_name, pattern in self.patterns.items():
                    matches = re.findall(pattern, text)
                    if matches:
                        stats[pattern_name] = len(matches)
                        for i, match in enumerate(matches):
                            if isinstance(match, tuple):
                                match = ''.join(match)
                            replacement = f"[{pattern_name.upper()}_{i+1}]"
                            replacement_map[match] = replacement
                            anonymized = anonymized.replace(match, replacement)
                
                # Custom patterns
                for custom_name, custom_pattern in self.custom_patterns:
                    matches = re.findall(custom_pattern, text)
                    if matches:
                        stats[custom_name] = len(matches)
                        for i, match in enumerate(matches):
                            if isinstance(match, tuple):
                                match = ''.join(match)
                            replacement = f"[CUSTOM_{custom_name.upper()}_{i+1}]"
                            replacement_map[match] = replacement
                            anonymized = anonymized.replace(match, replacement)
                
                # Save to history
                self.anonymization_history.append({
                    'timestamp': datetime.now(),
                    'original_length': len(text),
                    'anonymized_length': len(anonymized),
                    'replacements': len(replacement_map),
                    'stats': stats
                })
                
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(1.0, anonymized)
                
                # Show summary
                summary = f"\n\n{'='*50}\n"
                summary += "📊 ANONYMIZATION SUMMARY:\n"
                summary += f"• Original size: {len(text)} characters\n"
                summary += f"• Anonymized size: {len(anonymized)} characters\n"
                summary += f"• Replacements made: {len(replacement_map)}\n"
                if stats:
                    summary += "• Data types found:\n"
                    for data_type, count in stats.items():
                        summary += f"  - {data_type}: {count}\n"
                
                self.output_text.insert(tk.END, summary)
                
                self.parent.notification_system.add_notification(
                    "Anonymization Complete",
                    f"Made {len(replacement_map)} replacements",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Anonymization Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=anonymize, daemon=True).start()
    
    def manage_patterns(self):
        """Správa vlastných patternov"""
        pattern_window = tk.Toplevel(self.parent.root)
        pattern_window.title("Custom Patterns Manager")
        pattern_window.geometry("600x400")
        pattern_window.configure(bg=self.parent.colors['background'])
        
        tk.Label(
            pattern_window,
            text="🎯 CUSTOM PATTERNS MANAGEMENT",
            font=("Courier New", 14, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        ).pack(pady=10)
        
        # Patterns list
        list_frame = tk.Frame(pattern_window, bg=self.parent.colors['surface'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        patterns_list = scrolledtext.ScrolledText(
            list_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg='#1a1a1a',
            fg='white',
            height=10
        )
        patterns_list.pack(fill=tk.BOTH, expand=True)
        
        # Show current patterns
        patterns_text = "Built-in Patterns:\n" + "="*40 + "\n"
        for name, pattern in self.patterns.items():
            patterns_text += f"• {name}: {pattern}\n"
        
        patterns_text += "\nCustom Patterns:\n" + "="*40 + "\n"
        for name, pattern in self.custom_patterns:
            patterns_text += f"• {name}: {pattern}\n"
        
        patterns_list.insert(1.0, patterns_text)
        
        # Add pattern form
        form_frame = tk.Frame(pattern_window, bg=self.parent.colors['background'])
        form_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(form_frame, text="Name:", bg=self.parent.colors['background'], fg='white').grid(row=0, column=0, sticky='w')
        name_entry = tk.Entry(form_frame, width=20)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(form_frame, text="Regex Pattern:", bg=self.parent.colors['background'], fg='white').grid(row=1, column=0, sticky='w')
        pattern_entry = tk.Entry(form_frame, width=40)
        pattern_entry.grid(row=1, column=1, padx=5, pady=2)
        
        def add_pattern():
            name = name_entry.get().strip()
            pattern = pattern_entry.get().strip()
            if name and pattern:
                self.custom_patterns.append((name, pattern))
                pattern_window.destroy()
                self.parent.notification_system.add_notification(
                    "Pattern Added",
                    f"Added custom pattern: {name}",
                    'success'
                )
        
        tk.Button(
            form_frame,
            text="➕ ADD PATTERN",
            command=add_pattern,
            bg=self.parent.colors['primary'],
            fg='white'
        ).grid(row=2, column=1, pady=10)
    
    def show_statistics(self):
        """Zobrazí štatistiky anonymizácie"""
        if not self.anonymization_history:
            self.parent.notification_system.add_notification(
                "No History",
                "No anonymization history available",
                'info'
            )
            return
        
        stats_window = tk.Toplevel(self.parent.root)
        stats_window.title("Anonymization Statistics")
        stats_window.geometry("500x400")
        stats_window.configure(bg=self.parent.colors['background'])
        
        tk.Label(
            stats_window,
            text="📊 ANONYMIZATION STATISTICS",
            font=("Courier New", 14, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        ).pack(pady=10)
        
        stats_text = scrolledtext.ScrolledText(
            stats_window,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg='#1a1a1a',
            fg='white'
        )
        stats_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        total_sessions = len(self.anonymization_history)
        total_replacements = sum(session['replacements'] for session in self.anonymization_history)
        
        report = f"ANONYMIZATION HISTORY REPORT\n{'='*50}\n\n"
        report += f"Total Sessions: {total_sessions}\n"
        report += f"Total Replacements: {total_replacements}\n\n"
        report += "Session Details:\n" + "="*30 + "\n"
        
        for i, session in enumerate(self.anonymization_history[-10:]):  # Last 10 sessions
            report += f"\nSession {i+1}:\n"
            report += f"  Time: {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"  Original: {session['original_length']} chars\n"
            report += f"  Anonymized: {session['anonymized_length']} chars\n"
            report += f"  Replacements: {session['replacements']}\n"
            if session['stats']:
                report += "  Data Types:\n"
                for data_type, count in session['stats'].items():
                    report += f"    - {data_type}: {count}\n"
        
        stats_text.insert(1.0, report)
    
    def batch_process(self):
        """Batch spracovanie súborov"""
        files = filedialog.askopenfilenames(
            title="Select files for batch processing",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not files:
            return
        
        def process_batch():
            try:
                total_files = len(files)
                processed = 0
                
                for file_path in files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Anonymize content
                        anonymized = content
                        for pattern_name, pattern in self.patterns.items():
                            matches = re.findall(pattern, content)
                            for i, match in enumerate(matches):
                                if isinstance(match, tuple):
                                    match = ''.join(match)
                                replacement = f"[{pattern_name.upper()}_{i+1}]"
                                anonymized = anonymized.replace(match, replacement)
                        
                        # Save anonymized file
                        output_path = Path(file_path).parent / f"anonymized_{Path(file_path).name}"
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(anonymized)
                        
                        processed += 1
                        
                    except Exception as e:
                        self.parent.notification_system.add_notification(
                            "File Error",
                            f"Failed to process {Path(file_path).name}: {str(e)}",
                            'warning'
                        )
                
                self.parent.notification_system.add_notification(
                    "Batch Complete",
                    f"Processed {processed}/{total_files} files",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Batch Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=process_batch, daemon=True).start()
    
    def load_file(self):
        """Načíta súbor"""
        file_path = filedialog.askopenfilename(
            title="Select file to load",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.input_text.delete(1.0, tk.END)
                self.input_text.insert(1.0, content)
                
                self.parent.notification_system.add_notification(
                    "File Loaded",
                    f"Loaded {Path(file_path).name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Load Error",
                    str(e),
                    'critical'
                )
    
    def save_output(self):
        """Uloží výstup"""
        text = self.output_text.get(1.0, tk.END).strip()
        if not text:
            self.parent.notification_system.add_notification(
                "Empty Output",
                "Nothing to save",
                'warning'
            )
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save anonymized output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                self.parent.notification_system.add_notification(
                    "File Saved",
                    f"Saved to {Path(file_path).name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Save Error",
                    str(e),
                    'critical'
                )
    
    def export_report(self):
        """Exportuje report"""
        if not self.anonymization_history:
            self.parent.notification_system.add_notification(
                "No Data",
                "No anonymization history to export",
                'warning'
            )
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export report",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                # Generate HTML report
                html_content = self._generate_html_report()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                self.parent.notification_system.add_notification(
                    "Report Exported",
                    f"Report saved to {Path(file_path).name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Export Error",
                    str(e),
                    'critical'
                )
    
    def _generate_html_report(self):
        """Vygeneruje HTML report"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CYBRO Anonymization Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }
                .header { background: #1a1a2e; padding: 20px; border-radius: 10px; }
                .session { background: #2a2a3e; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .stats { color: #00ff9d; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔷 CYBRO Anonymization Report</h1>
                <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
        """
        
        for i, session in enumerate(self.anonymization_history):
            html += f"""
            <div class="session">
                <h3>Session {i+1}</h3>
                <p><strong>Time:</strong> {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Original Size:</strong> {session['original_length']} characters</p>
                <p><strong>Anonymized Size:</strong> {session['anonymized_length']} characters</p>
                <p><strong>Replacements:</strong> {session['replacements']}</p>
            </div>
            """
        
        html += "</body></html>"
        return html
    
    def clear_all(self):
        """Vyčistí všetko"""
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.parent.notification_system.add_notification(
            "Cleared",
            "All fields cleared",
            'info'
        )

class UltimateNetworkAnalyzer:
    def __init__(self, parent):
        self.parent = parent
        self.network_devices = []
        self.network_range = None
        self.gateway_ip = None
        self.local_mac = self._get_local_mac()
        self.watchdog_running = False
        self.watchdog_thread = None
        self.missing_counts = {}
        self.whitelist = []
        self.active_interface = None
        self.passive_capture = None
        self.passive_event_engine = None
        self.passive_queue = None
        self.passive_storage = None
        self.passive_registry = None
        self.passive_sensor_ready = False
        self.passive_last_event = None
        
        # Initialize network
        self.initialize_network()
        self._init_passive_sensor()
    
    def _get_local_mac(self):
        """Získa lokálnu MAC adresu"""
        try:
            import uuid
            mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
            return mac.upper()
        except:
            return "Unknown"
    
    def initialize_network(self):
        """Inicializuje sieťové nastavenia"""
        if not self.parent.has_sudo:
            return
        
        try:
            if sys.platform == "win32":
                # Windows network detection
                output = subprocess.check_output(['ipconfig', '/all']).decode()
                gateway_match = re.search(r'Default Gateway.*?(\d+\.\d+\.\d+\.\d+)', output)
                self.gateway_ip = gateway_match.group(1) if gateway_match else "192.168.1.1"
                self.network_range = "192.168.1.0/24"
            else:
                # Linux network detection
                output = subprocess.check_output(['ip', 'route']).decode()
                gateway_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', output)
                self.gateway_ip = gateway_match.group(1) if gateway_match else None
                
                range_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', output)
                self.network_range = range_match.group(1) if range_match else "192.168.1.0/24"
            
            self.parent.notification_system.add_notification(
                "Network Initialized",
                f"Gateway: {self.gateway_ip}, Range: {self.network_range}",
                'success'
            )

            self.active_interface = self._detect_active_interface()
            if self.active_interface:
                logger.info("Selected network interface: %s", self.active_interface)
            else:
                logger.warning("No active interface detected, using default Scapy interface")
            
            # Start monitoring
            self.start_network_monitoring()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Network Error",
                str(e),
                'critical'
            )

    def _init_passive_sensor(self):
        """Spustí pasívny sniffer a event engine."""
        if not self.parent.has_sudo:
            self.parent.notification_system.add_notification(
                "Requires sudo",
                "Requires sudo: passive network sensor (Scapy sniffing).",
                'warning',
                8000
            )
            return
        if not (SCAPY_AVAILABLE and PASSIVE_MODULES_AVAILABLE):
            return
        if self.passive_event_engine:
            return
        try:
            sensor_db = RUNTIME_ROOT / "passive_devices.db"
            self.passive_storage = DeviceStorage(sensor_db)
            self.passive_registry = DeviceRegistry(
                storage=self.passive_storage,
                vendor_resolver=OUIResolver(Path(__file__).resolve().parent / "oui_sample.csv"),
            )
            self.passive_queue = Queue()
            self.passive_capture = PassiveCapture(
                interface=self._choose_capture_interface(),
                observation_queue=self.passive_queue,
            )
            self.passive_event_engine = EventEngine(
                capture=self.passive_capture,
                registry=self.passive_registry,
                observation_queue=self.passive_queue,
                disappearance_timeout=900,
            )
            self.passive_event_engine.register_listener(self._handle_passive_event)
            self.passive_event_engine.start()
            self.passive_sensor_ready = True
            self.parent.notification_system.add_notification(
                "Passive Sensor",
                "Passive ARP/DHCP/DNS monitoring active",
                'success'
            )
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Passive Sensor Error",
                str(e),
                'critical'
            )

    def _choose_capture_interface(self):
        """Vyberie rozhranie pre pasívne snímanie."""
        try:
            from scapy.config import conf
            return conf.iface
        except Exception:
            return None

    def _handle_passive_event(self, event):
        """Spracuje udalosti z pasívneho engine."""
        if not self.parent or not hasattr(self.parent, "root"):
            return
        self.passive_last_event = event
        try:
            self.parent.root.after(0, lambda e=event: self._process_passive_event(e))
        except Exception:
            # Fallback ak root ešte neexistuje
            self._process_passive_event(event)

    def _process_passive_event(self, event):
        if DeviceEventType is None:
            return
        payload = event.payload or {}
        ip = payload.get("ip") or payload.get("new_ip")
        hostname = payload.get("hostname")
        if not hostname:
            hostnames = payload.get("hostnames")
            if isinstance(hostnames, list) and hostnames:
                hostname = hostnames[0]
        vendor = payload.get("vendor")
        protocols = payload.get("protocols") or []
        if not protocols and payload.get("protocol"):
            protocols = [payload["protocol"]]
        ip_history = payload.get("ip_history")
        self._merge_passive_device(
            mac=event.mac,
            ip=ip,
            hostname=hostname,
            vendor=vendor,
            last_seen=event.timestamp,
            ip_history=ip_history,
            protocols=protocols,
        )

        if event.event_type == DeviceEventType.OBSERVATION:
            return

        if LOCAL_AI_AVAILABLE and DeviceEventType and event.event_type in {
            DeviceEventType.NEW_DEVICE,
            DeviceEventType.DEVICE_REAPPEARED,
            DeviceEventType.IP_CHANGED,
        }:
            threading.Thread(
                target=self._run_ai_analysis,
                args=(event,),
                daemon=True,
            ).start()

        if event.event_type == DeviceEventType.NEW_DEVICE:
            message = f"Passive discovery: {ip or 'Unknown IP'} ({event.mac})"
            level = 'warning'
        elif event.event_type == DeviceEventType.DEVICE_REAPPEARED:
            message = f"Device reappeared: {ip or 'Unknown IP'} ({event.mac})"
            level = 'info'
        elif event.event_type == DeviceEventType.DEVICE_DISAPPEARED:
            last_seen = payload.get("last_seen")
            message = f"Device disappeared: {event.mac} last seen {last_seen}"
            level = 'critical'
        elif event.event_type == DeviceEventType.IP_CHANGED:
            new_ip = payload.get("new_ip", "Unknown")
            message = f"Device {event.mac} changed IP to {new_ip}"
            level = 'info'
        else:
            message = f"Passive event: {event.event_type.value} for {event.mac}"
            level = 'info'

        self.parent.notification_system.add_notification(
            "Passive Sensor Event",
            message,
            level,
            6000
        )

    def _merge_passive_device(
        self,
        mac,
        ip=None,
        hostname=None,
        vendor=None,
        last_seen=None,
        ip_history=None,
        protocols=None,
    ):
        if not mac:
            return
        hostname_value = hostname or "Unknown"
        vendor_value = vendor or "Unknown"
        seen = self._normalize_timestamp(last_seen)
        entry = next((d for d in self.network_devices if d.get("mac") == mac), None)
        if not entry and ip:
            entry = next((d for d in self.network_devices if d.get("ip") == ip), None)

        if entry:
            if ip:
                entry["ip"] = ip
            entry["mac"] = mac
            entry["hostname"] = hostname_value if hostname else entry.get("hostname", hostname_value)
            entry["vendor"] = vendor_value if vendor else entry.get("vendor", vendor_value)
            entry["last_seen"] = seen
            entry.setdefault("source", "passive")
            if hostname:
                history = entry.setdefault("hostname_history", [])
                if hostname not in history:
                    history.append(hostname)
            if ip_history:
                entry["ip_history"] = list(dict.fromkeys(ip_history))
            elif ip:
                ip_hist = entry.setdefault("ip_history", [])
                if ip not in ip_hist:
                    ip_hist.append(ip)
            if protocols:
                proto_set = set(entry.get("protocols", []))
                proto_set.update(protocols)
                entry["protocols"] = sorted(proto_set)
        else:
            entry = {
                "ip": ip or "Unknown",
                "mac": mac,
                "hostname": hostname_value,
                "vendor": vendor_value,
                "last_seen": seen,
                "source": "passive",
                "hostname_history": [hostname] if hostname else [],
                "ip_history": [ip] if ip else [],
                "protocols": sorted(set(protocols or [])),
            }
            self.network_devices.append(entry)
        self.refresh_devices()

    def _normalize_timestamp(self, value):
        if isinstance(value, datetime):
            ts = value
        elif isinstance(value, str):
            try:
                ts = datetime.fromisoformat(value)
            except ValueError:
                return datetime.now()
        else:
            return datetime.now()
        if ts.tzinfo:
            ts = ts.astimezone().replace(tzinfo=None)
        return ts

    def _run_ai_analysis(self, event):
        if not (LOCAL_AI_AVAILABLE and build_ai_context and build_ai_prompt and ai_analyze_event and normalize_insight):
            return
        try:
            context = build_ai_context(event, self.passive_registry)
            if not context:
                return
            prompt = build_ai_prompt(context)
            context_for_engine = dict(context)
            context_for_engine["prompt"] = prompt
            ai_raw = ai_analyze_event(context_for_engine)
            insight = normalize_insight(ai_raw)
        except Exception:
            return
        if not insight:
            return
        try:
            self.parent.root.after(
                0, lambda e=event, data=insight: self._handle_ai_insight(e, data)
            )
        except Exception:
            self._handle_ai_insight(event, insight)

    def _handle_ai_insight(self, event, insight):
        device = next((d for d in self.network_devices if d.get("mac") == event.mac), None)
        payload = event.payload or {}
        if not device and payload.get("ip"):
            device = next((d for d in self.network_devices if d.get("ip") == payload.get("ip")), None)
        if device is not None:
            device["ai_insight"] = insight
            device["ai_label"] = f"{insight['classification']}/{insight['risk']}"
            device["ai_explanation"] = insight["explanation"]
            self.refresh_devices()

        if insight.get("risk", "low") != "low":
            level = "critical" if insight["risk"] == "high" else "warning"
            message = (
                f"AI: {insight['classification']} device {event.mac} "
                f"flagged {insight['risk']} - {insight['explanation']} "
                f"(Action: {insight['recommended_action']})"
            )
            self.parent.notification_system.add_notification(
                "AI Network Insight",
                message,
                level,
                8000,
            )
    
    def start_network_monitoring(self):
        """Spustí monitoring siete"""
        if self.watchdog_running:
            return
        
        self.watchdog_running = True
        self.watchdog_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.watchdog_thread.start()
        
        self.parent.notification_system.add_notification(
            "Monitoring Started",
            "Network monitoring is now active",
            'success'
        )
    
    def _monitoring_loop(self):
        """Hlavná slučka monitoringu"""
        while self.watchdog_running:
            try:
                if SCAPY_AVAILABLE:
                    self._arp_scan()
                
                time.sleep(10)  # Scan every 10 seconds
                
            except Exception as e:
                logger.warning("Monitoring error: %s", e)
                time.sleep(30)
    
    def _arp_scan(self):
        """ARP skenovanie"""
        try:
            if not self.network_range:
                return
            
            # Create ARP request
            arp = ARP(pdst=self.network_range)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            
            # Send and receive
            interface = self.active_interface or conf.iface
            result = srp(packet, timeout=2, verbose=False, iface=interface)[0]
            
            current_devices = []
            for sent, received in result:
                device_info = {
                    'ip': received.psrc,
                    'mac': received.hwsrc,
                    'hostname': self._resolve_hostname(received.psrc),
                    'last_seen': datetime.now(),
                    'vendor': self._get_vendor_from_mac(received.hwsrc)
                }
                current_devices.append(device_info)
            
            self._update_device_list(current_devices)
            
        except Exception as e:
            if "No such device" not in str(e):
                logger.warning("ARP scan error: %s", e)

    def _detect_active_interface(self):
        try:
            output = subprocess.check_output(["ip", "-o", "-4", "addr", "show", "up"], text=True)
        except subprocess.CalledProcessError as err:
            logger.warning("Interface detection failed: %s", err)
            return None
        candidates = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[1].strip(":")
            if name == "lo":
                continue
            inet = parts[3]
            if inet.startswith("127."):
                continue
            score = 1 if name.startswith("wl") else 0
            candidates.append((score, name))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]
    
    def _resolve_hostname(self, ip):
        """Rozlíši hostname z IP"""
        try:
            import socket
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Unknown"
    
    def _get_vendor_from_mac(self, mac):
        """Získa výrobcu z MAC adresy"""
        # Simplified vendor lookup - in real implementation, use OUI database
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1C:42': 'Parallels',
            '00:1D:0F': 'Cisco',
            '00:24:8C': 'Dell'
        }
        
        mac_prefix = mac[:8].upper()
        return vendors.get(mac_prefix, 'Unknown')
    
    def _update_device_list(self, current_devices):
        """Aktualizuje zoznam zariadení"""
        new_devices = []
        
        for current in current_devices:
            existing = next(
                (
                    d
                    for d in self.network_devices
                    if d.get('ip') == current['ip'] or d.get('mac') == current['mac']
                ),
                None
            )
            
            if existing:
                # Update existing device
                existing.update(current)
            else:
                # New device found
                current['source'] = 'active'
                self.network_devices.append(current)
                new_devices.append(current)
                
                self.parent.notification_system.add_notification(
                    "New Device",
                    f"IP: {current['ip']}, MAC: {current['mac']}",
                    'warning'
                )
        
        # Check for missing devices
        current_ips = {d['ip'] for d in current_devices}
        for device in self.network_devices[:]:
            if device.get('source') == 'active' and device.get('ip') not in current_ips:
                self.missing_counts[device['ip']] = self.missing_counts.get(device['ip'], 0) + 1
                
                if self.missing_counts[device['ip']] > 3:  # Missing for 3 scans
                    self.parent.notification_system.add_notification(
                        "Device Missing",
                        f"IP: {device['ip']} has disappeared",
                        'critical'
                    )
                    self.network_devices.remove(device)
                    del self.missing_counts[device['ip']]
    
    def setup_ui(self, parent):
        """Nastaví UI pre sieťový analyzátor"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="🌐 ULTIMATE NETWORK ANALYZER - REAL-TIME MONITORING",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        # Network info
        info_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = f"""
📍 NETWORK INFORMATION:
• Gateway: {self.gateway_ip or 'Unknown'}
• Network Range: {self.network_range or 'Unknown'}  
• Local MAC: {self.local_mac}
• Monitoring: {'🟢 ACTIVE' if self.watchdog_running else '🔴 INACTIVE'}
• Passive Sensor: {'🟢 ONLINE' if self.passive_sensor_ready else '🔴 OFFLINE'}
• Devices Found: {len(self.network_devices)}
        """
        
        tk.Label(
            info_frame,
            text=info_text,
            font=("Courier New", 10),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary'],
            justify=tk.LEFT
        ).pack(padx=10, pady=10)
        
        # Control buttons
        control_frame = tk.Frame(parent, bg=self.parent.colors['background'])
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        buttons = [
            ("🔍 SCAN NETWORK", self.scan_network),
            ("📡 PACKET CAPTURE", self.packet_capture),
        ]
        if self.parent.advanced_tools_visible:
            buttons.extend(
                [
                    ("🛡️ VULNERABILITY SCAN", self.vulnerability_scan),
                    ("📊 TRAFFIC ANALYSIS", self.traffic_analysis),
                    ("🎯 PORT SCAN", self.port_scan),
                ]
            )
        
        for i, (text, command) in enumerate(buttons):
            btn = tk.Button(
                control_frame,
                text=text,
                command=command,
                font=("Courier New", 9, "bold"),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=15,
                pady=8
            )
            btn.grid(row=0, column=i, padx=5, pady=5)

        monitor_frame = tk.Frame(parent, bg=self.parent.colors['background'])
        monitor_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(
            monitor_frame,
            text="Dedicated Wi-Fi adapter (monitor mode)",
            font=("Courier New", 9),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['text_secondary']
        ).pack(side=tk.LEFT, padx=5)
        self.parent.wifi_monitor_button = tk.Button(
            monitor_frame,
            text=self.parent._wifi_monitor_button_text(),
            command=self.parent.toggle_wifi_monitor_mode,
            font=("Courier New", 10, "bold"),
            bg=self.parent.colors['primary'],
            fg=self.parent.colors['background'],
            relief='flat',
            padx=15,
            pady=6
        )
        self.parent.wifi_monitor_button.pack(side=tk.RIGHT, padx=5)
        
        # Devices list
        devices_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            devices_frame,
            text="📱 NETWORK DEVICES:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        # Create treeview for devices
        columns = ("IP", "MAC", "Hostname", "Vendor", "Last Seen")
        self.devices_tree = ttk.Treeview(devices_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.devices_tree.heading(col, text=col)
            self.devices_tree.column(col, width=120)
        
        # Context menu for device actions
        self.tree_context_menu = tk.Menu(self.devices_tree, tearoff=0)
        self.tree_context_menu.add_command(
            label="Open in Browser",
            command=self.open_selected_in_browser
        )
        
        def show_context_menu(event):
            selection = self.devices_tree.identify_row(event.y)
            if selection:
                self.devices_tree.selection_set(selection)
                self.tree_context_menu.post(event.x_root, event.y_root)
        
        self.devices_tree.bind("<Button-3>", show_context_menu)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(devices_frame, orient="vertical", command=self.devices_tree.yview)
        self.devices_tree.configure(yscrollcommand=scrollbar.set)
        
        self.devices_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        tk.Button(
            devices_frame,
            text="🔄 REFRESH",
            command=self.refresh_devices,
            font=("Courier New", 9),
            bg=self.parent.colors['accent'],
            fg='white',
            relief='flat',
            padx=10,
            pady=5
        ).pack(pady=5)
        
        # Initial devices load
        self.refresh_devices()
    
    def refresh_devices(self):
        """Obnoví zoznam zariadení"""
        if not hasattr(self, "devices_tree"):
            return
        if not self.devices_tree.winfo_exists():
            return
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        for device in self.network_devices:
            vendor_display = device.get('vendor', 'Unknown')
            if device.get('ai_label'):
                vendor_display = f"{vendor_display} [{device['ai_label']}]"
            last_seen = device.get('last_seen', datetime.now())
            self.devices_tree.insert("", "end", values=(
                device['ip'],
                device['mac'],
                device.get('hostname', 'Unknown'),
                vendor_display,
                last_seen.strftime("%H:%M:%S")
            ))
    
    def open_selected_in_browser(self):
        """Otvára vybrané zariadenie vo webovom prehliadači"""
        try:
            selected_items = self.devices_tree.selection()
            if not selected_items:
                raise IndexError
            
            device_ip = self.devices_tree.item(selected_items[0])['values'][0]
            if not device_ip:
                self.parent.notification_system.add_notification(
                    "Error",
                    "Could not get IP address",
                    'warning'
                )
                return
            
            url = f"http://{device_ip}"
            webbrowser.open(url)
            
            self.parent.notification_system.add_notification(
                "Browser Opened",
                f"Opening {url} in browser",
                'info'
            )
        
        except IndexError:
            self.parent.notification_system.add_notification(
                "No Selection",
                "Please select a device first",
                'warning'
            )
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Error",
                f"Could not open browser: {e}",
                'critical'
            )
    
    def scan_network(self):
        """Komplexné skenovanie siete"""
        def perform_scan():
            try:
                if not self.network_range:
                    self.parent.notification_system.add_notification(
                        "Network Scan",
                        "Unknown network range - run analyzer with sudo.",
                        'warning'
                    )
                    return
                
                self.parent.notification_system.add_notification(
                    "Network Scan",
                    "Starting targeted camera scan...",
                    'info'
                )
                
                scan_command = [
                    'nmap',
                    '-p', '80,443,554,8000,37777,3702,8080',
                    '-sV',
                    '-T4',
                    self.network_range
                ]
                
                try:
                    result = subprocess.run(
                        scan_command,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                except FileNotFoundError:
                    self.parent.notification_system.add_notification(
                        "Nmap Required",
                        "Install nmap to enable camera scanning.",
                        'critical'
                    )
                    return
                
                output = result.stdout or ""
                camera_keywords = [
                    'hikvision', 'dahua', 'axis', 'onvif',
                    'rtsp', 'ip camera', 'network video'
                ]
                
                ip_service_map = {}
                current_ip = None
                current_lines = []
                for line in output.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Nmap scan report for"):
                        if current_ip and current_lines:
                            ip_service_map[current_ip] = " ".join(current_lines)
                        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', stripped)
                        current_ip = ip_match.group(1) if ip_match else None
                        current_lines = []
                    elif stripped.startswith("Nmap done:"):
                        if current_ip and current_lines:
                            ip_service_map[current_ip] = " ".join(current_lines)
                        current_ip = None
                        current_lines = []
                    elif current_ip:
                        current_lines.append(stripped)
                if current_ip and current_lines:
                    ip_service_map[current_ip] = " ".join(current_lines)
                
                detected_cameras = []
                
                for ip, description in ip_service_map.items():
                    lower_desc = description.lower()
                    matched_keyword = next(
                        (kw for kw in camera_keywords if kw in lower_desc),
                        None
                    )
                    if not matched_keyword:
                        continue
                    
                    vendor_label = f"Kamera ({matched_keyword.title()})"
                    device_found = False
                    for device in self.network_devices:
                        if device['ip'] == ip:
                            device['vendor'] = vendor_label
                            device_found = True
                            break
                    if not device_found:
                        self.network_devices.append({
                            'ip': ip,
                            'mac': 'Unknown',
                            'hostname': 'Unknown',
                            'vendor': vendor_label,
                            'last_seen': datetime.now()
                        })
                    detected_cameras.append(f"{ip} - {vendor_label}")
                
                if detected_cameras:
                    self.parent.notification_system.add_notification(
                        "Cameras Detected",
                        " | ".join(detected_cameras),
                        'warning'
                    )
                else:
                    self.parent.notification_system.add_notification(
                        "Scan Complete",
                        "No camera signatures detected on scanned ports.",
                        'info'
                    )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Scan Error",
                    str(e),
                    'critical'
                )
            finally:
                self.parent.root.after(0, self.refresh_devices)
        
        threading.Thread(target=perform_scan, daemon=True).start()
    
    def packet_capture(self):
        """Zachytávanie paketov"""
        if not SCAPY_AVAILABLE:
            self.parent.notification_system.add_notification(
                "Scapy Required",
                "Install scapy for packet capture",
                'warning'
            )
            return
        
        def capture_packets():
            try:
                self.parent.notification_system.add_notification(
                    "Packet Capture",
                    "Starting packet capture...",
                    'info'
                )
                
                # Capture 100 packets
                packets = sniff(count=100, timeout=30)
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = CAPTURE_DIR / f"capture_{timestamp}.pcap"
                wrpcap(str(filename), packets)
                
                self.parent.notification_system.add_notification(
                    "Capture Complete",
                    f"Saved {len(packets)} packets to {filename.name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Capture Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=capture_packets, daemon=True).start()
    
    def vulnerability_scan(self):
        """Skenovanie zraniteľností"""
        def vuln_scan():
            try:
                self.parent.notification_system.add_notification(
                    "Vulnerability Scan",
                    "Starting vulnerability assessment...",
                    'info'
                )
                
                if self.network_range:
                    # Use nmap vulnerability scripts
                    result = subprocess.run(
                        ['nmap', '--script', 'vuln', self.network_range],
                        capture_output=True, text=True, timeout=600
                    )
                    
                    # Parse results
                    vulnerabilities = re.findall(r'CVE-\d{4}-\d+', result.stdout)
                    
                    self.parent.notification_system.add_notification(
                        "Vuln Scan Complete",
                        f"Found {len(vulnerabilities)} potential vulnerabilities",
                        'success' if not vulnerabilities else 'critical'
                    )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Vuln Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=vuln_scan, daemon=True).start()
    
    def traffic_analysis(self):
        """Analýza sieťového prevádzky"""
        self.parent.notification_system.add_notification(
            "Traffic Analysis",
            "Traffic analysis feature - Coming soon!",
            'info'
        )
    
    def port_scan(self):
        """Skenovanie portov"""
        def port_scanning():
            try:
                self.parent.notification_system.add_notification(
                    "Port Scan",
                    "Starting port scan...",
                    'info'
                )
                
                if self.gateway_ip:
                    # Scan common ports
                    result = subprocess.run(
                        ['nmap', '-p', '1-1000', self.gateway_ip],
                        capture_output=True, text=True, timeout=180
                    )
                    
                    open_ports = re.findall(r'(\d+)/tcp.*open', result.stdout)
                    
                    self.parent.notification_system.add_notification(
                        "Port Scan Complete",
                        f"Found {len(open_ports)} open ports on gateway",
                        'success' if not open_ports else 'warning'
                    )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Port Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=port_scanning, daemon=True).start()

class UltimateIsolationTester:
    def __init__(self, parent):
        self.parent = parent
        self.local_ip = self._get_local_ip()
        self.target_entry = None
        self.local_ip_label = None
        self.log_output = None
        self.test_thread = None
    
    def _get_local_ip(self):
        """Zistí lokálnu IP adresu pomocou UDP socketu"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "Unknown"
    
    def setup_ui(self, parent):
        """Nastaví UI pre test izolácie sietí"""
        self.parent.clear_content()
        self.local_ip = self._get_local_ip()
        
        header = tk.Label(
            parent,
            text="🌐 ULTIMATE NETWORK ISOLATION TESTER",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        description = tk.Label(
            parent,
            text="Analyzuje prepojenie medzi vašou lokálnou sieťou a cieľovou podsieťou pomocou ping a traceroute.",
            font=("Courier New", 10),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['text_secondary']
        )
        description.pack(pady=(0, 10))
        
        input_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            input_frame,
            text="🎯 CIEĽOVÁ IP (v druhej sieti):",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        self.target_entry = tk.Entry(
            input_frame,
            width=30,
            font=("Courier New", 11)
        )
        self.target_entry.grid(row=0, column=1, padx=10, pady=10)
        self.target_entry.insert(0, "192.168.2.10")
        
        tk.Label(
            input_frame,
            text="🛰️ VAŠA LOKÁLNA IP:",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        
        self.local_ip_label = tk.Label(
            input_frame,
            text=self.local_ip,
            font=("Courier New", 11),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary']
        )
        self.local_ip_label.grid(row=1, column=1, sticky="w", padx=10, pady=10)
        
        start_button = tk.Button(
            input_frame,
            text="🚀 SPustiť test izolácie",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['accent'],
            fg='white',
            relief='flat',
            padx=15,
            pady=10,
            command=self.run_isolation_test
        )
        start_button.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky="nsew")
        
        input_frame.grid_columnconfigure(2, weight=1)
        
        log_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            log_frame,
            text="📋 TESTOVACÍ LOG:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=10)
        
        self.log_output = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg='#0f0f1a',
            fg='#00ff9d',
            state=tk.DISABLED,
            height=20
        )
        self.log_output.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
    
    def run_isolation_test(self):
        """Spustí test v samostatnom vlákne"""
        if not self.target_entry:
            return
        
        target_ip = self.target_entry.get().strip()
        if not target_ip:
            messagebox.showwarning("Chýba cieľ", "Zadajte prosím IP adresu zariadenia v cieľovej sieti.")
            return
        
        if self.test_thread and self.test_thread.is_alive():
            messagebox.showinfo("Test prebieha", "Počkajte prosím na dokončenie aktuálneho testu.")
            return
        
        self._log("\n" + "=" * 60)
        self._log(f"🚀 Spúšťam test izolácie pre cieľ {target_ip}")
        self._log(f"🛰️ Lokálna IP: {self.local_ip}")
        
        self.test_thread = threading.Thread(
            target=self._perform_isolation_test,
            args=(target_ip,),
            daemon=True
        )
        self.test_thread.start()
    
    def _perform_isolation_test(self, target_ip):
        """Vykoná ping a traceroute na pozadí"""
        ping_cmd = ['ping', '-n', '3', target_ip] if sys.platform == "win32" else ['ping', '-c', '3', target_ip]
        self._log(f"📡 Spúšťam ping: {' '.join(ping_cmd)}")
        
        try:
            ping_result = subprocess.run(
                ping_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            self._log(ping_result.stdout.strip() or ping_result.stderr.strip() or "Žiadny výstup z ping.")
            
            if ping_result.returncode != 0:
                self._log("✅ HODNOTENIE: SIETE SÚ PRAVDEPODOBNE IZOLOVANÉ. (Ping zlyhal)")
                return
        except FileNotFoundError:
            self._log("❌ Ping nástroj nie je dostupný v systéme.")
            return
        except subprocess.TimeoutExpired:
            self._log("❌ Ping prekročil časový limit.")
            self._log("✅ HODNOTENIE: SIETE SÚ PRAVDEPODOBNE IZOLOVANÉ. (Ping zlyhal)")
            return
        except Exception as exc:
            self._log(f"❌ Chyba pri pingu: {exc}")
            self._log("✅ HODNOTENIE: SIETE SÚ PRAVDEPODOBNE IZOLOVANÉ. (Ping zlyhal)")
            return
        
        trace_cmd = ['tracert', target_ip] if sys.platform == "win32" else ['traceroute', target_ip]
        self._log(f"🛰️ Spúšťam traceroute: {' '.join(trace_cmd)}")
        
        try:
            trace_result = subprocess.run(
                trace_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            trace_output = trace_result.stdout or trace_result.stderr or ""
            self._log(trace_output.strip() or "Žiadny výstup z traceroute.")
            hop_count = self._count_hops(trace_output)
        except FileNotFoundError:
            self._log("❌ Traceroute/tracert nie je dostupný. Nainštalujte ho pre úplný test.")
            self._log("⚠️ HODNOTENIE: NEMOŽNO URČIŤ PREPOJENIE BEZ TRACEROUTE.")
            return
        except subprocess.TimeoutExpired:
            self._log("❌ Traceroute prekročil časový limit.")
            self._log("⚠️ HODNOTENIE: NEMOŽNO URČIŤ PREPOJENIE (Traceroute timeout).")
            return
        except Exception as exc:
            self._log(f"❌ Chyba pri traceroute: {exc}")
            self._log("⚠️ HODNOTENIE: NEMOŽNO URČIŤ PREPOJENIE (Traceroute zlyhal).")
            return
        
        if hop_count == 1:
            self._log("❌ BEZPEČNOSTNÁ CHYBA: SIETE SÚ PREMOSTENÉ (BRIDGED)! (Detekovaný 1 skok, cieľ je na L2)")
        elif hop_count > 1:
            self._log(f"⚠️ HODNOTENIE: SIETE SÚ PREPOJENÉ (ROUTOVANÉ). (Detekovaných {hop_count} skokov cez router)")
        else:
            self._log("⚠️ HODNOTENIE: NEPODARILO SA DETEGOVAŤ SKOKY. VÝSLEDOK NIE JE PRESNÝ.")
    
    def _count_hops(self, trace_output):
        """Spočíta počet platných hopov z traceroute výstupu"""
        hop_count = 0
        for line in trace_output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^(\d+)\s+', line)
            if match:
                hop_count += 1
        return hop_count
    
    def _log(self, message):
        """Bezpečne zapíše správu do logu z ľubovoľného vlákna"""
        if not self.log_output:
            return
        
        def append():
            self.log_output.config(state=tk.NORMAL)
            self.log_output.insert(tk.END, message + "\n")
            self.log_output.see(tk.END)
            self.log_output.config(state=tk.DISABLED)
        
        self.parent.root.after(0, append)

class UltimateBluetoothRadar:
    def __init__(self, parent):
        self.parent = parent
        self.bluetooth_devices = []
        self.scanning = False
        self.ble_client = None
    
    def setup_ui(self, parent):
        """Nastaví UI pre Bluetooth radar"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="📡 ULTIMATE BLUETOOTH RADAR - BLE DEVICE DISCOVERY",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        if not BLE_AVAILABLE:
            warning_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
            warning_frame.pack(fill=tk.X, padx=20, pady=20)
            
            tk.Label(
                warning_frame,
                text="⚠️ BLUETOOTH MODULES NOT AVAILABLE\nInstall: pip install bleak",
                font=("Courier New", 14),
                bg=self.parent.colors['surface'],
                fg='#ff6b6b',
                justify=tk.CENTER
            ).pack(pady=20)
            return
        
        # Control panel
        control_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Scan controls
        scan_frame = tk.Frame(control_frame, bg=self.parent.colors['surface'])
        scan_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(
            scan_frame,
            text="🔍 START BLE SCAN",
            command=self.start_ble_scan,
            font=("Courier New", 10, "bold"),
            bg=self.parent.colors['primary'],
            fg=self.parent.colors['background'],
            relief='flat',
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            scan_frame,
            text="🛑 STOP SCAN",
            command=self.stop_ble_scan,
            font=("Courier New", 10),
            bg=self.parent.colors['accent'],
            fg='white',
            relief='flat',
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        # Scan duration
        duration_frame = tk.Frame(control_frame, bg=self.parent.colors['surface'])
        duration_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            duration_frame,
            text="Scan Duration (seconds):",
            font=("Courier New", 9),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary']
        ).pack(side=tk.LEFT, padx=5)
        
        self.scan_duration = tk.Entry(duration_frame, width=5)
        self.scan_duration.pack(side=tk.LEFT, padx=5)
        self.scan_duration.insert(0, "10")
        
        # Devices list
        devices_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            devices_frame,
            text="📱 DISCOVERED BLE DEVICES:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        # Treeview for BLE devices
        columns = ("Name", "Address", "RSSI", "Services")
        self.ble_tree = ttk.Treeview(devices_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.ble_tree.heading(col, text=col)
            self.ble_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(devices_frame, orient="vertical", command=self.ble_tree.yview)
        self.ble_tree.configure(yscrollcommand=scrollbar.set)
        
        self.ble_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Device actions
        actions_frame = tk.Frame(parent, bg=self.parent.colors['background'])
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        action_buttons = [
            ("📋 GET SERVICES", self.get_device_services),
            ("🔗 CONNECT", self.connect_to_device),
            ("📊 DEVICE INFO", self.get_device_info),
            ("💾 EXPORT SCAN", self.export_ble_scan)
        ]
        
        for i, (text, command) in enumerate(action_buttons):
            btn = tk.Button(
                actions_frame,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=10,
                pady=6
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
    
    def start_ble_scan(self):
        """Spustí BLE skenovanie"""
        if self.scanning:
            return
        
        def scan():
            try:
                self.scanning = True
                duration = int(self.scan_duration.get() or 10)
                
                self.parent.notification_system.add_notification(
                    "BLE Scan Started",
                    f"Scanning for BLE devices for {duration} seconds...",
                    'info'
                )
                
                # Clear previous results
                self.bluetooth_devices.clear()
                for item in self.ble_tree.get_children():
                    self.ble_tree.delete(item)
                
                async def run_scan():
                    scanner = BleakScanner()
                    devices = await scanner.discover(timeout=duration)
                    
                    for device in devices:
                        device_info = {
                            'name': device.name or "Unknown",
                            'address': device.address,
                            'rssi': device.rssi if hasattr(device, 'rssi') else 'N/A',
                            'services': []
                        }
                        self.bluetooth_devices.append(device_info)
                    
                    # Update UI
                    self.parent.root.after(0, self._update_ble_list)
                
                # Run async scan
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_scan())
                
                self.scanning = False
                self.parent.notification_system.add_notification(
                    "BLE Scan Complete",
                    f"Found {len(self.bluetooth_devices)} BLE devices",
                    'success'
                )
                
            except Exception as e:
                self.scanning = False
                self.parent.notification_system.add_notification(
                    "BLE Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=scan, daemon=True).start()
    
    def stop_ble_scan(self):
        """Zastaví BLE skenovanie"""
        self.scanning = False
        self.parent.notification_system.add_notification(
            "BLE Scan Stopped",
            "Bluetooth scanning stopped",
            'info'
        )
    
    def _update_ble_list(self):
        """Aktualizuje zoznam BLE zariadení"""
        for item in self.ble_tree.get_children():
            self.ble_tree.delete(item)
        
        for device in self.bluetooth_devices:
            self.ble_tree.insert("", "end", values=(
                device['name'],
                device['address'],
                device['rssi'],
                len(device['services'])
            ))
    
    def get_device_services(self):
        """Získa služby vybraného zariadenia"""
        selection = self.ble_tree.selection()
        if not selection:
            self.parent.notification_system.add_notification(
                "No Selection",
                "Please select a BLE device first",
                'warning'
            )
            return
        
        item = self.ble_tree.item(selection[0])
        device_address = item['values'][1]
        
        def get_services():
            try:
                async def run_service_scan():
                    async with BleakClient(device_address) as client:
                        services = await client.get_services()
                        service_list = []
                        for service in services:
                            service_list.append(service.uuid)
                        
                        # Update device info
                        for device in self.bluetooth_devices:
                            if device['address'] == device_address:
                                device['services'] = service_list
                                break
                        
                        # Show services in messagebox
                        services_text = f"Services for {device_address}:\n\n"
                        for service in service_list:
                            services_text += f"• {service}\n"
                        
                        self.parent.root.after(0, lambda: messagebox.showinfo("BLE Services", services_text))
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_service_scan())
                
            except Exception as e:
                self.parent.root.after(0, lambda: messagebox.showerror("BLE Error", f"Failed to get services: {e}"))
        
        threading.Thread(target=get_services, daemon=True).start()
    
    def connect_to_device(self):
        """Pripojí sa k BLE zariadeniu"""
        selection = self.ble_tree.selection()
        if not selection:
            self.parent.notification_system.add_notification(
                "No Selection",
                "Please select a BLE device first",
                'warning'
            )
            return
        
        item = self.ble_tree.item(selection[0])
        device_address = item['values'][1]
        device_name = item['values'][0]
        
        def connect():
            try:
                async def run_connect():
                    self.ble_client = BleakClient(device_address)
                    await self.ble_client.connect()
                    
                    self.parent.root.after(0, lambda: self.parent.notification_system.add_notification(
                        "BLE Connected",
                        f"Connected to {device_name}",
                        'success'
                    ))
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_connect())
                
            except Exception as e:
                self.parent.root.after(0, lambda: self.parent.notification_system.add_notification(
                    "Connection Failed",
                    f"Failed to connect: {e}",
                    'critical'
                ))
        
        threading.Thread(target=connect, daemon=True).start()
    
    def get_device_info(self):
        """Získa informácie o zariadení"""
        selection = self.ble_tree.selection()
        if not selection:
            self.parent.notification_system.add_notification(
                "No Selection",
                "Please select a BLE device first",
                'warning'
            )
            return
        
        item = self.ble_tree.item(selection[0])
        device_info = f"""
Device Information:
Name: {item['values'][0]}
Address: {item['values'][1]}
RSSI: {item['values'][2]}
Services: {item['values'][3]}
        """
        
        messagebox.showinfo("BLE Device Info", device_info)
    
    def export_ble_scan(self):
        """Exportuje výsledky BLE skenu"""
        if not self.bluetooth_devices:
            self.parent.notification_system.add_notification(
                "No Data",
                "No BLE devices to export",
                'warning'
            )
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export BLE Scan",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Address', 'RSSI', 'Services Count'])
                    
                    for device in self.bluetooth_devices:
                        writer.writerow([
                            device['name'],
                            device['address'],
                            device['rssi'],
                            len(device['services'])
                        ])
                
                self.parent.notification_system.add_notification(
                    "Export Complete",
                    f"BLE scan exported to {Path(file_path).name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Export Error",
                    str(e),
                    'critical'
                )

class UltimatePentestToolkit:
    def __init__(self, parent):
        self.parent = parent
        self.pentest_results = []
        self.current_scan = None
    
    def setup_ui(self, parent):
        """Nastaví UI pre pentest toolkit"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="🛡️ ULTIMATE PENTEST TOOLKIT - PROFESSIONAL SECURITY TESTING",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        # Warning frame
        warning_frame = tk.Frame(parent, bg='#2a1a1a')
        warning_frame.pack(fill=tk.X, padx=20, pady=10)
        
        warning_text = """
⚠️ LEGAL AND ETHICAL USE ONLY
This toolkit is for authorized security testing only.
You MUST have explicit permission to test any system.
Unauthorized access is illegal and unethical.
        """
        
        tk.Label(
            warning_frame,
            text=warning_text,
            font=("Courier New", 10),
            bg='#2a1a1a',
            fg='#ff6b6b',
            justify=tk.CENTER
        ).pack(padx=10, pady=10)
        
        # Target input
        target_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        target_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            target_frame,
            text="🎯 TARGET:",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        self.target_entry = tk.Entry(target_frame, width=30, font=("Courier New", 10))
        self.target_entry.grid(row=0, column=1, padx=5, pady=5)
        self.target_entry.insert(0, "example.com")
        
        # Pentest categories
        categories_frame = tk.Frame(parent, bg=self.parent.colors['background'])
        categories_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create notebook for categories
        notebook = ttk.Notebook(categories_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Network Testing tab
        network_frame = tk.Frame(notebook, bg=self.parent.colors['background'])
        notebook.add(network_frame, text="🌐 NETWORK TESTING")
        self.setup_network_testing(network_frame)
        
        # Web Application tab
        web_frame = tk.Frame(notebook, bg=self.parent.colors['background'])
        notebook.add(web_frame, text="🕸️ WEB APPLICATION")
        self.setup_web_testing(web_frame)
        
        # Wireless Testing tab
        wireless_frame = tk.Frame(notebook, bg=self.parent.colors['background'])
        notebook.add(wireless_frame, text="📡 WIRELESS TESTING")
        self.setup_wireless_testing(wireless_frame)
        
        # Output area
        output_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        output_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            output_frame,
            text="PENTEST OUTPUT:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        self.pentest_output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg='#1a1a1a',
            fg='#00ff00',
            height=15
        )
        self.pentest_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_network_testing(self, parent):
        """Nastaví sieťové testovanie"""
        network_tests = [
            ("🔍 PORT SCAN", self.port_scan),
            ("🛡️ VULNERABILITY SCAN", self.vulnerability_scan),
            ("🌐 SERVICE DETECTION", self.service_detection),
            ("📊 OS FINGERPRINTING", self.os_fingerprinting),
            ("🔒 FIREWALL DETECTION", self.firewall_detection)
        ]
        
        for i, (text, command) in enumerate(network_tests):
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=10,
                pady=8,
                width=20
            )
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5)
    
    def setup_web_testing(self, parent):
        """Nastaví webové testovanie"""
        web_tests = [
            ("🔐 SSL/TLS TEST", self.ssl_test),
            ("🛡️ SECURITY HEADERS", self.security_headers),
            ("💉 SQL INJECTION", self.sql_injection_test),
            ("📝 XSS TESTING", self.xss_testing),
            ("📁 DIRECTORY BRUTEFORCE", self.directory_bruteforce)
        ]
        
        for i, (text, command) in enumerate(web_tests):
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.parent.colors['accent'],
                fg='white',
                relief='flat',
                padx=10,
                pady=8,
                width=20
            )
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5)
    
    def setup_wireless_testing(self, parent):
        """Nastaví bezdrôtové testovanie"""
        wireless_tests = [
            ("📶 WIFI SCAN", self.wifi_scan),
            ("🔓 WPS TEST", self.wps_test),
            ("📡 ROGUE AP DETECTION", self.rogue_ap_detection),
            ("🔑 WPA/WPA2 TEST", self.wpa_test)
        ]
        
        for i, (text, command) in enumerate(wireless_tests):
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=10,
                pady=8,
                width=20
            )
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5)
    
    def port_scan(self):
        """Skenovanie portov"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target",
                'warning'
            )
            return
        
        def scan_ports():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, f"🔍 Starting port scan on {target}...\n\n")
                
                # Common ports scan
                result = subprocess.run(
                    ['nmap', '-p', '1-1000', target],
                    capture_output=True, text=True, timeout=300
                )
                
                self.pentest_output.insert(tk.END, result.stdout)
                
                # Parse open ports
                open_ports = re.findall(r'(\d+)/tcp.*open', result.stdout)
                
                self.pentest_results.append({
                    'type': 'port_scan',
                    'target': target,
                    'timestamp': datetime.now(),
                    'open_ports': open_ports
                })
                
                self.parent.notification_system.add_notification(
                    "Port Scan Complete",
                    f"Found {len(open_ports)} open ports on {target}",
                    'success' if not open_ports else 'warning'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ Port scan error: {e}\n")
                self.parent.notification_system.add_notification(
                    "Port Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=scan_ports, daemon=True).start()
    
    def vulnerability_scan(self):
        """Skenovanie zraniteľností"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target",
                'warning'
            )
            return
        
        def scan_vulns():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, f"🛡️ Starting vulnerability scan on {target}...\n\n")
                
                # Nmap vulnerability scripts
                result = subprocess.run(
                    ['nmap', '--script', 'vuln', target],
                    capture_output=True, text=True, timeout=600
                )
                
                self.pentest_output.insert(tk.END, result.stdout)
                
                # Parse CVEs
                cves = re.findall(r'(CVE-\d{4}-\d+)', result.stdout)
                
                self.pentest_results.append({
                    'type': 'vulnerability_scan',
                    'target': target,
                    'timestamp': datetime.now(),
                    'cves_found': cves
                })
                
                self.parent.notification_system.add_notification(
                    "Vuln Scan Complete",
                    f"Found {len(cves)} CVEs on {target}",
                    'success' if not cves else 'critical'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ Vulnerability scan error: {e}\n")
                self.parent.notification_system.add_notification(
                    "Vuln Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=scan_vulns, daemon=True).start()
    
    def service_detection(self):
        """Detekcia služieb"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target",
                'warning'
            )
            return
        
        def detect_services():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, f"🔧 Starting service detection on {target}...\n\n")
                
                # Service version detection
                result = subprocess.run(
                    ['nmap', '-sV', target],
                    capture_output=True, text=True, timeout=300
                )
                
                self.pentest_output.insert(tk.END, result.stdout)
                
                self.parent.notification_system.add_notification(
                    "Service Detection Complete",
                    f"Service detection finished for {target}",
                    'success'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ Service detection error: {e}\n")
                self.parent.notification_system.add_notification(
                    "Service Detection Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=detect_services, daemon=True).start()
    
    def ssl_test(self):
        """Test SSL/TLS"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target",
                'warning'
            )
            return
        
        def test_ssl():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, f"🔐 Testing SSL/TLS on {target}...\n\n")
                
                # SSL scan using sslscan if available
                result = subprocess.run(
                    ['sslscan', target],
                    capture_output=True, text=True, timeout=120
                )
                
                self.pentest_output.insert(tk.END, result.stdout)
                
                self.parent.notification_system.add_notification(
                    "SSL Test Complete",
                    f"SSL/TLS test finished for {target}",
                    'success'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ SSL test error: {e}\n")
                self.pentest_output.insert(tk.END, "💡 Install sslscan: sudo apt install sslscan\n")
                self.parent.notification_system.add_notification(
                    "SSL Test Error",
                    str(e),
                    'warning'
                )
        
        threading.Thread(target=test_ssl, daemon=True).start()
    
    def security_headers(self):
        """Kontrola bezpečnostných hlavičiek"""
        target = self.target_entry.get().strip()
        if not target.startswith(('http://', 'https://')):
            target = 'https://' + target
        
        def check_headers():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, f"🛡️ Checking security headers for {target}...\n\n")
                
                # Use curl to get headers
                result = subprocess.run(
                    ['curl', '-I', target],
                    capture_output=True, text=True, timeout=30
                )
                
                self.pentest_output.insert(tk.END, result.stdout)
                
                # Analyze headers
                headers = result.stdout.lower()
                missing_headers = []
                
                security_headers = [
                    'content-security-policy',
                    'x-frame-options', 
                    'x-content-type-options',
                    'strict-transport-security',
                    'x-xss-protection'
                ]
                
                for header in security_headers:
                    if header not in headers:
                        missing_headers.append(header)
                
                if missing_headers:
                    self.pentest_output.insert(tk.END, f"\n⚠️ MISSING SECURITY HEADERS: {', '.join(missing_headers)}\n")
                
                self.parent.notification_system.add_notification(
                    "Headers Check Complete",
                    f"Security headers checked for {target}",
                    'success' if not missing_headers else 'warning'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ Headers check error: {e}\n")
                self.parent.notification_system.add_notification(
                    "Headers Check Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=check_headers, daemon=True).start()
    
    def sql_injection_test(self):
        """Základný SQL injection test"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target URL",
                'warning'
            )
            return
        
        self.pentest_output.insert(tk.END, f"💉 SQL Injection testing for {target}...\n")
        self.pentest_output.insert(tk.END, "🔧 This feature requires manual testing or sqlmap installation\n")
        self.pentest_output.insert(tk.END, "💡 Install: pip install sqlmap\n")
        self.pentest_output.insert(tk.END, "💡 Usage: sqlmap -u '{target}' --batch\n")
    
    def xss_testing(self):
        """Základný XSS test"""
        target = self.target_entry.get().strip()
        if not target:
            self.parent.notification_system.add_notification(
                "No Target",
                "Please enter a target URL",
                'warning'
            )
            return
        
        self.pentest_output.insert(tk.END, f"📝 XSS testing for {target}...\n")
        self.pentest_output.insert(tk.END, "🔧 Manual testing required for comprehensive XSS assessment\n")
        self.pentest_output.insert(tk.END, "💡 Test payloads: <script>alert('XSS')</script>\n")
        self.pentest_output.insert(tk.END, "💡 Use tools: XSStrike, xsser\n")
    
    def wifi_scan(self):
        """WiFi skenovanie"""
        if not self.parent.has_sudo:
            self.parent.notification_system.add_notification(
                "Sudo Required",
                "WiFi scanning requires sudo privileges",
                'warning'
            )
            return
        
        def scan_wifi():
            try:
                self.pentest_output.delete(1.0, tk.END)
                self.pentest_output.insert(tk.END, "📶 Scanning WiFi networks...\n\n")
                
                if sys.platform == "linux":
                    result = subprocess.run(
                        ['nmcli', 'dev', 'wifi', 'list'],
                        capture_output=True, text=True, timeout=60
                    )
                    self.pentest_output.insert(tk.END, result.stdout)
                else:
                    self.pentest_output.insert(tk.END, "❌ WiFi scanning not supported on this platform\n")
                
                self.parent.notification_system.add_notification(
                    "WiFi Scan Complete",
                    "WiFi network scan finished",
                    'success'
                )
                
            except Exception as e:
                self.pentest_output.insert(tk.END, f"❌ WiFi scan error: {e}\n")
                self.parent.notification_system.add_notification(
                    "WiFi Scan Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=scan_wifi, daemon=True).start()
    
    # Placeholder methods for other tests
    def os_fingerprinting(self):
        self.pentest_output.insert(tk.END, "🌐 OS Fingerprinting - Use: nmap -O target\n")
    
    def firewall_detection(self):
        self.pentest_output.insert(tk.END, "🔒 Firewall Detection - Use: nmap -sA target\n")
    
    def directory_bruteforce(self):
        self.pentest_output.insert(tk.END, "📁 Directory Bruteforce - Use: dirb, gobuster, or dirsearch\n")
    
    def wps_test(self):
        self.pentest_output.insert(tk.END, "🔓 WPS Testing - Use: wash, reaver, or bully\n")
    
    def rogue_ap_detection(self):
        self.pentest_output.insert(tk.END, "📡 Rogue AP Detection - Manual monitoring required\n")
    
    def wpa_test(self):
        self.pentest_output.insert(tk.END, "🔑 WPA/WPA2 Testing - Use: aircrack-ng suite\n")

class UltimateReportingSystem:
    def __init__(self, parent):
        self.parent = parent
    
    def setup_ui(self, parent):
        """Nastaví UI pre reportovací systém"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="📊 ULTIMATE REPORTING SYSTEM - SECURITY ASSESSMENT REPORTS",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        # Report types
        reports_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        reports_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        report_types = [
            ("🎭 ANONYMIZATION REPORT", self.generate_anonymization_report),
            ("🌐 NETWORK ASSESSMENT", self.generate_network_report),
            ("🤖 AI ANALYSIS REPORT", self.generate_ai_report),
            ("📡 BLE SECURITY REPORT", self.generate_ble_report),
            ("🛡️ PENTEST REPORT", self.generate_pentest_report),
            ("📈 COMPREHENSIVE SECURITY", self.generate_comprehensive_report)
        ]
        
        for i, (text, command) in enumerate(report_types):
            btn = tk.Button(
                reports_frame,
                text=text,
                command=command,
                font=("Courier New", 10, "bold"),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=20,
                pady=15,
                width=25
            )
            btn.grid(row=i // 2, column=i % 2, padx=10, pady=10)
        
        # Recent reports
        recent_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            recent_frame,
            text="📋 RECENTLY GENERATED REPORTS:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        # List of recent reports
        self.reports_list = tk.Listbox(
            recent_frame,
            bg='#1a1a1a',
            fg='white',
            font=("Consolas", 9),
            height=8
        )
        self.reports_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Load existing reports
        self.load_recent_reports()
    
    def load_recent_reports(self):
        """Načíta nedávne reporty"""
        self.reports_list.delete(0, tk.END)
        
        try:
            report_files = list(REPORTS_DIR.glob("*.html")) + list(REPORTS_DIR.glob("*.pdf"))
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for report_file in report_files[:10]:  # Show last 10 reports
                self.reports_list.insert(tk.END, f"{report_file.name} - {datetime.fromtimestamp(report_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
        
        except Exception as e:
            self.reports_list.insert(tk.END, f"Error loading reports: {e}")
    
    def generate_anonymization_report(self):
        """Vygeneruje report z anonymizácie"""
        if not hasattr(self.parent, 'anonymizer') or not self.parent.anonymizer.anonymization_history:
            self.parent.notification_system.add_notification(
                "No Data",
                "No anonymization history available",
                'warning'
            )
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"anonymization_report_{timestamp}.html"
            
            html_content = self.parent.anonymizer._generate_html_report()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.parent.notification_system.add_notification(
                "Report Generated",
                f"Anonymization report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Report Error",
                str(e),
                'critical'
            )
    
    def generate_network_report(self):
        """Vygeneruje sieťový report"""
        if not hasattr(self.parent, 'network_analyzer') or not self.parent.network_analyzer.network_devices:
            self.parent.notification_system.add_notification(
                "No Data",
                "No network scan data available",
                'warning'
            )
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"network_report_{timestamp}.html"
            
            devices = self.parent.network_analyzer.network_devices
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CYBRO Network Assessment Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }}
                    .header {{ background: #1a1a2e; padding: 20px; border-radius: 10px; }}
                    .device {{ background: #2a2a3e; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                    .stats {{ color: #00ff9d; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔷 CYBRO Network Assessment Report</h1>
                    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>Devices Found: {len(devices)}</p>
                </div>
            """
            
            for i, device in enumerate(devices):
                html += f"""
                <div class="device">
                    <h3>Device {i+1}</h3>
                    <p><strong>IP:</strong> {device['ip']}</p>
                    <p><strong>MAC:</strong> {device['mac']}</p>
                    <p><strong>Hostname:</strong> {device.get('hostname', 'Unknown')}</p>
                    <p><strong>Vendor:</strong> {device.get('vendor', 'Unknown')}</p>
                    <p><strong>Last Seen:</strong> {device.get('last_seen', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                """
            
            html += "</body></html>"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.parent.notification_system.add_notification(
                "Network Report Generated",
                f"Network report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Network Report Error",
                str(e),
                'critical'
            )

    def generate_ai_report(self):
        report_lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines.append("CYBRO AI Analysis Report")
        report_lines.append(f"Generated: {now}")
        report_lines.append("=" * 90)

        network = getattr(self.parent, "network_analyzer", None)
        if network:
            report_lines.append("NETWORK STATUS")
            report_lines.append(f"Gateway: {network.gateway_ip or 'Unknown'}")
            report_lines.append(f"Network Range: {network.network_range or 'Unknown'}")
            report_lines.append(f"Devices Detected: {len(network.network_devices)}")
            report_lines.append(f"Passive Sensor: {'Online' if network.passive_sensor_ready else 'Offline'}")
            report_lines.append("")
            if network.network_devices:
                report_lines.append("Observed Devices:")
                for device in network.network_devices[:25]:
                    mac = device.get('mac', 'Unknown')
                    ip = device.get('ip', 'Unknown')
                    vendor = device.get('vendor', 'Unknown')
                    last_seen = device.get('last_seen')
                    last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if isinstance(last_seen, datetime) else "Unknown"
                    report_lines.append(f" - {ip:<15} {mac:<18} Vendor: {vendor} Last: {last_seen_str}")
                if len(network.network_devices) > 25:
                    report_lines.append(f"   ... {len(network.network_devices) - 25} more")
                report_lines.append("")

        ble_radar = getattr(self.parent, "bluetooth_radar", None)
        if ble_radar:
            devices = getattr(ble_radar, "bluetooth_devices", [])
            report_lines.append("BLUETOOTH LOW ENERGY OVERVIEW")
            report_lines.append(f"BLE Devices Discovered: {len(devices)}")
            for ble in devices[:20]:
                name = ble.get('name') or 'Unknown'
                addr = ble.get('address') or 'Unknown'
                rssi = ble.get('rssi', 'n/a')
                report_lines.append(f" - {addr:<18} RSSI: {rssi:<4}  Name: {name}")
            if len(devices) > 20:
                report_lines.append(f"   ... {len(devices) - 20} more")
            report_lines.append("")

        report_lines.append("SYSTEM HEALTH")
        report_lines.append(f"Has Sudo: {'Yes' if self.parent.has_sudo else 'No'}")
        report_lines.append(f"Local AI Analyst: {'Ready' if LOCAL_AI_AVAILABLE else 'Offline'}")
        report_lines.append(f"Network Module: {'Available' if SCAPY_AVAILABLE else 'Unavailable'}")
        report_lines.append(f"BLE Module: {'Available' if BLE_AVAILABLE else 'Unavailable'}")
        report_lines.append("")

        wifi_sensor = getattr(self.parent, "network_analyzer", None)
        wifi_panel = getattr(self.parent, "wifi_presence_panel", None)
        wifi_monitor_sensor = getattr(wifi_panel, "sensor", None) if wifi_panel else None
        if wifi_monitor_sensor:
            report_lines.append("WI-FI PRESENCE")
            report_lines.append(f"Devices tracked: {len(wifi_monitor_sensor.devices)}")
            for device in list(wifi_monitor_sensor.devices.values())[:25]:
                status = "PRESENT" if device.get('present') else "LOST"
                mac = device.get('mac')
                rssi = device.get('rssi')
                channel = device.get('channel')
                last_seen = device.get('last_seen')
                last_seen_str = last_seen.strftime("%H:%M:%S") if isinstance(last_seen, datetime) else "Unknown"
                report_lines.append(f" - {mac}  RSSI: {rssi}  Channel: {channel}  Status: {status}  Last: {last_seen_str}")
        report_lines.append("")

        report_lines.append("RECENT ALERTS")
        notifications = getattr(self.parent.notification_system, "notifications", [])
        for note in notifications[-10:]:
            report_lines.append(f"[{note.get('timestamp')}] {note.get('title')}: {note.get('message')}")

        threat_score, threat_summary = self._calculate_threat_score(network, devices if network else [], wifi_monitor_sensor, notifications)
        report_lines.insert(3, f"Threat Score: {threat_score}/100")
        report_lines.insert(4, f"Threat Summary: {threat_summary}")
        report_lines.insert(5, "")

        report_text = "\n".join(report_lines)

        window = tk.Toplevel(self.parent.root)
        window.title("AI Analysis Report")
        window.geometry("900x600")
        text_widget = scrolledtext.ScrolledText(window, wrap=tk.WORD, font=("Courier New", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, report_text)
        text_widget.config(state=tk.DISABLED)

        def export_report() -> None:
            from tkinter import messagebox

            try:
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = REPORTS_DIR / f"ai_analysis_report_{timestamp}.txt"
                with open(file_path, "w", encoding="utf-8") as handle:
                    handle.write(report_text)
                messagebox.showinfo(
                    "AI Analysis Report",
                    f"Report exported to {file_path.name}"
                )
            except Exception as err:
                messagebox.showerror(
                    "Export Failed",
                    f"Could not export report: {err}"
                )

        tk.Button(
            window,
            text="Export to TXT",
            command=export_report,
            font=("Courier New", 10, "bold"),
            bg="#00ff9d",
            fg="#0a0a12",
            relief='flat',
            padx=12,
            pady=6
        ).pack(pady=8)

    def _calculate_threat_score(self, network, devices, wifi_monitor_sensor, notifications):
        score = 0
        summary = []

        if network and devices:
            unknown_devices = [d for d in devices if (d.get('vendor') in (None, 'Unknown'))]
            score += min(len(unknown_devices) * 2, 25)
            if unknown_devices:
                summary.append(f"Unknown devices: {len(unknown_devices)}")

        if wifi_monitor_sensor:
            lost = [d for d in wifi_monitor_sensor.devices.values() if not d.get('present')]
            new_devices = [d for d in wifi_monitor_sensor.devices.values() if d.get('frame_count', 0) <= 3]
            score += min(len(lost) * 2, 20)
            score += min(len(new_devices) * 2, 20)
            if lost:
                summary.append(f"Lost Wi-Fi devices: {len(lost)}")
            if new_devices:
                summary.append(f"New Wi-Fi devices: {len(new_devices)}")

        ble_radar = getattr(self.parent, "bluetooth_radar", None)
        if ble_radar:
            anomalies = [d for d in ble_radar.bluetooth_devices if isinstance(d.get('rssi'), (int, float)) and d['rssi'] > -30]
            score += min(len(anomalies) * 3, 15)
            if anomalies:
                summary.append(f"BLE proximity alerts: {len(anomalies)}")

        alert_count = len(notifications[-20:])
        score += min(alert_count * 2, 20)
        if alert_count:
            summary.append(f"Recent alerts: {alert_count}")

        score = min(score, 100)
        if not summary:
            summary.append("No immediate anomalies detected.")
        return score, "; ".join(summary)
    
    def generate_ble_report(self):
        """Vygeneruje BLE report"""
        if not hasattr(self.parent, 'bluetooth_radar') or not self.parent.bluetooth_radar.bluetooth_devices:
            self.parent.notification_system.add_notification(
                "No Data",
                "No BLE scan data available",
                'warning'
            )
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"ble_report_{timestamp}.html"
            
            devices = self.parent.bluetooth_radar.bluetooth_devices
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CYBRO BLE Security Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }}
                    .header {{ background: #1a1a2e; padding: 20px; border-radius: 10px; }}
                    .device {{ background: #2a2a3e; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔷 CYBRO BLE Security Report</h1>
                    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>BLE Devices Found: {len(devices)}</p>
                </div>
            """
            
            for i, device in enumerate(devices):
                html += f"""
                <div class="device">
                    <h3>BLE Device {i+1}</h3>
                    <p><strong>Name:</strong> {device['name']}</p>
                    <p><strong>Address:</strong> {device['address']}</p>
                    <p><strong>RSSI:</strong> {device['rssi']}</p>
                    <p><strong>Services:</strong> {len(device['services'])}</p>
                </div>
                """
            
            html += "</body></html>"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.parent.notification_system.add_notification(
                "BLE Report Generated",
                f"BLE security report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "BLE Report Error",
                str(e),
                'critical'
            )
    
    def generate_pentest_report(self):
        """Vygeneruje pentest report"""
        if not hasattr(self.parent, 'pentest_toolkit') or not self.parent.pentest_toolkit.pentest_results:
            self.parent.notification_system.add_notification(
                "No Data",
                "No pentest results available",
                'warning'
            )
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"pentest_report_{timestamp}.html"
            
            results = self.parent.pentest_toolkit.pentest_results
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CYBRO Pentest Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }}
                    .header {{ background: #1a1a2e; padding: 20px; border-radius: 10px; }}
                    .result {{ background: #2a2a3e; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                    .critical {{ border-left: 4px solid #F44336; }}
                    .warning {{ border-left: 4px solid #FF9800; }}
                    .info {{ border-left: 4px solid #2196F3; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔷 CYBRO Pentest Report</h1>
                    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>Total Tests: {len(results)}</p>
                </div>
            """
            
            for i, result in enumerate(results):
                severity = 'critical' if result.get('cves_found') else 'info'
                
                html += f"""
                <div class="result {severity}">
                    <h3>Test {i+1}: {result['type'].replace('_', ' ').title()}</h3>
                    <p><strong>Target:</strong> {result['target']}</p>
                    <p><strong>Time:</strong> {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                """
            
            html += "</body></html>"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.parent.notification_system.add_notification(
                "Pentest Report Generated",
                f"Pentest report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Pentest Report Error",
                str(e),
                'critical'
            )
    
    def generate_comprehensive_report(self):
        """Vygeneruje komplexný security report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"comprehensive_security_report_{timestamp}.html"
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CYBRO Comprehensive Security Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }}
                    .header {{ background: #1a1a2e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                    .section {{ background: #2a2a3e; margin: 15px 0; padding: 20px; border-radius: 5px; }}
                    .stats {{ color: #00ff9d; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔷 CYBRO Comprehensive Security Report</h1>
                    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>Complete security assessment overview</p>
                </div>
            """
            
            # Network section
            if hasattr(self.parent, 'network_analyzer'):
                html += f"""
                <div class="section">
                    <h2>🌐 Network Assessment</h2>
                    <p><span class="stats">Devices Found:</span> {len(self.parent.network_analyzer.network_devices)}</p>
                    <p><span class="stats">Network Range:</span> {self.parent.network_analyzer.network_range or 'Unknown'}</p>
                    <p><span class="stats">Gateway:</span> {self.parent.network_analyzer.gateway_ip or 'Unknown'}</p>
                </div>
                """
            
            # Anonymization section
            if hasattr(self.parent, 'anonymizer'):
                html += f"""
                <div class="section">
                    <h2>🎭 Data Anonymization</h2>
                    <p><span class="stats">Total Sessions:</span> {len(self.parent.anonymizer.anonymization_history)}</p>
                    <p><span class="stats">Total Replacements:</span> {sum(session['replacements'] for session in self.parent.anonymizer.anonymization_history)}</p>
                </div>
                """
            
            # BLE section
            if hasattr(self.parent, 'bluetooth_radar'):
                html += f"""
                <div class="section">
                    <h2>📡 Bluetooth Security</h2>
                    <p><span class="stats">BLE Devices Found:</span> {len(self.parent.bluetooth_radar.bluetooth_devices)}</p>
                </div>
                """
            
            # Pentest section
            if hasattr(self.parent, 'pentest_toolkit'):
                html += f"""
                <div class="section">
                    <h2>🛡️ Penetration Testing</h2>
                    <p><span class="stats">Tests Performed:</span> {len(self.parent.pentest_toolkit.pentest_results)}</p>
                </div>
                """
            
            html += """
                <div class="section">
                    <h2>💡 Security Recommendations</h2>
                    <ul>
                        <li>Regularly update all systems and software</li>
                        <li>Implement strong access controls</li>
                        <li>Monitor network traffic for anomalies</li>
                        <li>Conduct regular security assessments</li>
                        <li>Educate users about security best practices</li>
                        <li>Backup critical data regularly</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.parent.notification_system.add_notification(
                "Comprehensive Report Generated",
                f"Complete security report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Comprehensive Report Error",
                str(e),
                'critical'
            )

class UltimateSettings:
    def __init__(self, parent):
        self.parent = parent
        self.config = self.load_config()
    
    def load_config(self):
        """Načíta konfiguráciu"""
        default_config = {
            'theme': 'cyberpunk',
            'auto_scan': True,
            'scan_interval': 30,
            'notifications': True,
            'log_level': 'INFO'
        }
        
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'r') as f:
                    return json.load(f)
        except:
            pass
        
        return default_config
    
    def save_config(self):
        """Uloží konfiguráciu"""
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error("Config save error: %s", e)
    
    def setup_ui(self, parent):
        """Nastaví UI pre nastavenia"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="⚙️ ULTIMATE SETTINGS - SYSTEM CONFIGURATION",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        # Settings container
        settings_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Theme settings
        theme_frame = tk.Frame(settings_frame, bg=self.parent.colors['surface'])
        theme_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            theme_frame,
            text="🎨 THEME:",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(side=tk.LEFT)
        
        theme_var = tk.StringVar(value=self.config.get('theme', 'cyberpunk'))
        themes = [('Cyberpunk', 'cyberpunk'), ('Dark', 'dark'), ('Light', 'light')]
        
        for text, value in themes:
            tk.Radiobutton(
                theme_frame,
                text=text,
                variable=theme_var,
                value=value,
                bg=self.parent.colors['surface'],
                fg=self.parent.colors['text_primary'],
                selectcolor=self.parent.colors['primary']
            ).pack(side=tk.LEFT, padx=10)
        
        # Auto-scan settings
        scan_frame = tk.Frame(settings_frame, bg=self.parent.colors['surface'])
        scan_frame.pack(fill=tk.X, padx=10, pady=10)
        
        auto_scan_var = tk.BooleanVar(value=self.config.get('auto_scan', True))
        tk.Checkbutton(
            scan_frame,
            text="🔄 AUTO NETWORK SCAN",
            variable=auto_scan_var,
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary'],
            selectcolor=self.parent.colors['primary']
        ).pack(side=tk.LEFT)
        
        tk.Label(
            scan_frame,
            text="Interval (seconds):",
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary']
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        scan_interval_var = tk.StringVar(value=str(self.config.get('scan_interval', 30)))
        scan_interval_entry = tk.Entry(
            scan_frame,
            textvariable=scan_interval_var,
            width=5
        )
        scan_interval_entry.pack(side=tk.LEFT)
        
        # Notification settings
        notif_frame = tk.Frame(settings_frame, bg=self.parent.colors['surface'])
        notif_frame.pack(fill=tk.X, padx=10, pady=10)
        
        notif_var = tk.BooleanVar(value=self.config.get('notifications', True))
        tk.Checkbutton(
            notif_frame,
            text="🔔 ENABLE NOTIFICATIONS",
            variable=notif_var,
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary'],
            selectcolor=self.parent.colors['primary']
        ).pack(side=tk.LEFT)
        
        # Log level
        log_frame = tk.Frame(settings_frame, bg=self.parent.colors['surface'])
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            log_frame,
            text="📝 LOG LEVEL:",
            font=("Courier New", 11, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(side=tk.LEFT)
        
        log_var = tk.StringVar(value=self.config.get('log_level', 'INFO'))
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        
        log_combo = ttk.Combobox(
            log_frame,
            textvariable=log_var,
            values=log_levels,
            state='readonly',
            width=10
        )
        log_combo.pack(side=tk.LEFT, padx=10)
        
        # Save button
        def save_settings():
            self.config.update({
                'theme': theme_var.get(),
                'auto_scan': auto_scan_var.get(),
                'scan_interval': int(scan_interval_var.get()),
                'notifications': notif_var.get(),
                'log_level': log_var.get()
            })
            self.save_config()
            
            self.parent.notification_system.add_notification(
                "Settings Saved",
                "Configuration updated successfully",
                'success'
            )
        
        save_btn = tk.Button(
            settings_frame,
            text="💾 SAVE SETTINGS",
            command=save_settings,
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['primary'],
            fg=self.parent.colors['background'],
            relief='flat',
            padx=20,
            pady=10
        )
        save_btn.pack(pady=20)
        
        # System info
        info_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        sys_info = f"""
System Information:
• Platform: {sys.platform}
• Python: {sys.version.split()[0]}
• Sudo: {'Available' if self.parent.has_sudo else 'Not Available'}
• Local AI Analyst: {'Ready' if LOCAL_AI_AVAILABLE else 'Offline'}
• Network: {'Available' if SCAPY_AVAILABLE else 'Not Available'}
• Bluetooth: {'Available' if BLE_AVAILABLE else 'Not Available'}
• Working Directory: {Path.cwd()}
        """
        
        tk.Label(
            info_frame,
            text=sys_info,
            font=("Courier New", 9),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['text_primary'],
            justify=tk.LEFT
        ).pack(padx=10, pady=10)

class UltimateCyberpunkGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔷 CYBRO WatchDog v7.0 - ULTIMATE CYBER SECURITY SUITE")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a12')
        
        # Cyberpunk farby
        self.colors = {
            'primary': '#00ff9d',
            'background': '#0a0a12',
            'surface': '#1a1a2e',
            'text_primary': '#ffffff',
            'text_secondary': '#b0b0cc',
            'accent': '#ff009d',
            'hacker': '#9C27B0'
        }
        
        # Kontrola sudo
        self.has_sudo = os.geteuid() == 0 if sys.platform != "win32" else True
        
        # Inicializácia systémov
        self.notification_system = UltimateNotificationSystem(self)
        self.anonymizer = UltimateAnonymizer(self)
        self.network_analyzer = UltimateNetworkAnalyzer(self)
        self.isolation_tester = UltimateIsolationTester(self)
        self.bluetooth_radar = UltimateBluetoothRadar(self)
        self.pentest_toolkit = UltimatePentestToolkit(self)
        self.reporting_system = UltimateReportingSystem(self)
        self.settings = UltimateSettings(self)
        self.advanced_tools_visible = False
        self.active_panel = "dashboard"
        self.advanced_frame = None
        self.advanced_toggle_btn = None
        self.wifi_monitor_enabled = False
        self.wifi_monitor_interface: Optional[str] = None
        self.wifi_monitor_button: Optional[tk.Button] = None
        self._wifi_toggle_in_progress = False
        self.ai_chat_window = None
        self.ai_chat_history = []
        self.ai_chat_context_paths = set()
        self.ai_chat_extra_context_sections = {}
        self.ai_chat_busy = False
        self.ai_chat_model_var = tk.StringVar(master=self.root, value=self._default_ai_chat_model())
        self.ai_chat_owner_mode_var = tk.BooleanVar(master=self.root, value=True)
        self.ai_chat_cloud_assist_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_anonymize_before_send_var = tk.BooleanVar(master=self.root, value=True)
        self.ai_chat_send_scope_var = tk.StringVar(master=self.root, value="message")
        self.ai_chat_cloud_model_var = tk.StringVar(master=self.root, value="gpt-5")
        self.ai_chat_cloud_include_snapshot_var = tk.BooleanVar(master=self.root, value=True)
        self.ai_chat_cloud_include_device_ips_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_cloud_include_db_overview_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_cloud_include_reports_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_cloud_include_logs_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_cloud_include_recent_artifacts_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_cloud_include_history_var = tk.BooleanVar(master=self.root, value=False)
        self.ai_chat_status_var = tk.StringVar(master=self.root, value="Context: 0 items")
        self.ai_chat_transcript = None
        self.ai_chat_input = None
        self.ai_chat_send_button = None
        self.ai_chat_preview_button = None
        self.ai_chat_cloud_send_button = None
        self.ai_chat_anonymize_check = None
        self.ai_chat_scope_message_radio = None
        self.ai_chat_scope_convo_radio = None
        self.ai_chat_cloud_model_entry = None
        self.ai_chat_cloud_whitelist_controls = []
        self.ai_chat_cloud_anonymize_override = False
        self.ai_chat_last_cloud_preview_text = ""
        self.ai_chat_last_cloud_preview_timestamp = 0.0
        self.ai_chat_last_cloud_preview_meta = {}
        self.ai_chat_last_cloud_preview_hash = ""
        self.ai_chat_last_cloud_preview_chars = 0
        self.ai_chat_last_cloud_preview_flags = {}
        self.voice_mode_var = tk.StringVar(master=self.root, value="ptt")
        self.voice_auto_send_var = tk.BooleanVar(master=self.root, value=False)
        self.voice_recording = False
        self.voice_proc = None
        self.voice_last_file = ""
        self.ai_chat_voice_mode_menu = None
        self.ai_chat_voice_button = None
        self.ai_chat_voice_auto_send_check = None

        self.setup_gui()
        
        # Štartovacie notifikácie
        self.root.after(1000, self.show_startup_notifications)
        
    def show_startup_notifications(self):
        """Zobrazí štartovacie notifikácie"""
        self.notification_system.add_notification(
            "System Initialized", 
            "CYBRO WatchDog v7.0 Ultimate Edition Ready",
            'success',
            5000
        )
        
        # System status notifications
        if not self.has_sudo:
            self.notification_system.add_notification(
                "Limited Mode",
                "Running without sudo - some features disabled",
                'warning',
                8000
            )

        if RUNTIME_FALLBACK_USED:
            self.notification_system.add_notification(
                "Storage Fallback",
                "Project write paths are not writable; using ~/.cache/cybro.",
                'warning',
                9000
            )
        
        
        if not SCAPY_AVAILABLE:
            self.notification_system.add_notification(
                "Network Analysis",
                "Scapy not available - network features limited",
                'warning'
            )
        
        if not BLE_AVAILABLE:
            self.notification_system.add_notification(
                "Bluetooth",
                "BLE features disabled - install bleak",
                'info'
            )
        
        if not PASSIVE_MODULES_AVAILABLE:
            self.notification_system.add_notification(
                "Passive Sensor",
                f"Passive monitoring modules unavailable: {passive_import_error}",
                'warning',
                10000
            )
        
        if not LOCAL_AI_AVAILABLE:
            self.notification_system.add_notification(
                "AI Analyst",
                f"Local AI unavailable: {local_ai_error}",
                'info',
                9000
            )
    
    def setup_gui(self):
        """Inicializácia GUI"""
        self.create_header()
        self.create_sidebar()
        self.create_main_content()
        
    def create_header(self):
        header = tk.Frame(self.root, bg=self.colors['surface'], height=80)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)
        
        # Left side - Title
        title_frame = tk.Frame(header, bg=self.colors['surface'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        title = tk.Label(
            title_frame,
            text="🔷 CYBRO WatchDog v7.0",
            font=("Courier New", 16, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['primary']
        )
        title.pack(pady=10)
        
        subtitle = tk.Label(
            title_frame,
            text="ULTIMATE CYBER SECURITY SUITE",
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        )
        subtitle.pack()
        
        # Right side - Status
        status_frame = tk.Frame(header, bg=self.colors['surface'])
        status_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20)
        
        sudo_status = "🟢 SUDO PRIVILEGES" if self.has_sudo else "🔴 NO SUDO"
        status_label = tk.Label(
            status_frame,
            text=sudo_status,
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['primary'] if self.has_sudo else '#ff6b6b'
        )
        status_label.pack(pady=5)
        
        # System time
        self.time_label = tk.Label(
            status_frame,
            text=datetime.now().strftime("%H:%M:%S"),
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        )
        self.time_label.pack()
        
        # Update time
        self.update_time()
    
    def update_time(self):
        """Aktualizuje čas v headeri"""
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_time)
    
    def create_sidebar(self):
        sidebar = tk.Frame(self.root, bg=self.colors['surface'], width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        sidebar.pack_propagate(False)
        
        sidebar_header = tk.Label(
            sidebar,
            text="NAVIGATION",
            font=("Courier New", 12, "bold"),
            bg=self.colors['primary'],
            fg=self.colors['background'],
            pady=10
        )
        sidebar_header.pack(fill=tk.X)

        observe_buttons = [
            ("🏠 DASHBOARD", self.show_dashboard),
            ("🌐 NETWORK ANALYZER", self.show_network_analyzer),
            ("📊 SECURITY REPORTS", self.show_reports),
            ("🤖 AI CHAT", self.open_ai_chat),
        ]

        for text, command in observe_buttons:
            btn = tk.Button(
                sidebar,
                text=text,
                command=command,
                font=("Courier New", 10),
                bg=self.colors['surface'],
                fg=self.colors['text_primary'],
                relief='flat',
                anchor='w',
                padx=20,
                pady=12,
                width=20
            )
            btn.pack(fill=tk.X, padx=5, pady=2)

        self.advanced_toggle_btn = tk.Button(
            sidebar,
            text="🧰 Advanced Tools (Show)",
            command=self.toggle_advanced_tools,
            font=("Courier New", 10, "bold"),
            bg=self.colors['primary'],
            fg=self.colors['background'],
            relief='flat',
            padx=20,
            pady=10
        )
        self.advanced_toggle_btn.pack(fill=tk.X, padx=5, pady=10)

        self.advanced_frame = tk.Frame(sidebar, bg=self.colors['surface'])
        tk.Label(
            self.advanced_frame,
            text="Advanced operations", 
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        ).pack(fill=tk.X, padx=10, pady=(0, 6))

        advanced_buttons = [
            ("🎭 ULTIMATE ANONYMIZER", self.show_anonymizer),
            ("🛰️ ISOLATION TESTER", self.show_isolation_tester),
            ("📡 BLE RADAR", self.show_bluetooth),
            ("🛡️ PENTEST TOOLKIT", self.show_pentest_toolkit),
            ("⚙️ SYSTEM SETTINGS", self.show_settings),
        ]

        for text, command in advanced_buttons:
            btn = tk.Button(
                self.advanced_frame,
                text=text,
                command=command,
                font=("Courier New", 10),
                bg=self.colors['surface'],
                fg=self.colors['text_primary'],
                relief='flat',
                anchor='w',
                padx=20,
                pady=10,
                width=20
            )
            btn.pack(fill=tk.X, padx=5, pady=2)

        # System info
        info_frame = tk.Frame(sidebar, bg=self.colors['surface'])
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        sys_info = f"""
System Status:
• Sudo: {'✅' if self.has_sudo else '❌'}
• Local AI Analyst: {'✅' if LOCAL_AI_AVAILABLE else '❌'}
• Network: {'✅' if SCAPY_AVAILABLE else '❌'}
• Bluetooth: {'✅' if BLE_AVAILABLE else '❌'}
        """
        
        tk.Label(
            info_frame,
            text=sys_info,
            font=("Courier New", 8),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary'],
            justify=tk.LEFT
        ).pack(padx=10, pady=10)

        self._sync_advanced_visibility()
    
    def create_main_content(self):
        self.content = tk.Frame(self.root, bg=self.colors['background'])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.show_dashboard()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def toggle_advanced_tools(self):
        self.advanced_tools_visible = not self.advanced_tools_visible
        self._sync_advanced_visibility()
        if self.active_panel == "dashboard":
            self.show_dashboard()
        elif self.active_panel == "network":
            self.show_network_analyzer()

    def _sync_advanced_visibility(self):
        if self.advanced_toggle_btn:
            text = "🧰 Advanced Tools (Hide)" if self.advanced_tools_visible else "🧰 Advanced Tools (Show)"
            self.advanced_toggle_btn.config(text=text)
        if self.advanced_frame:
            if self.advanced_tools_visible and not self.advanced_frame.winfo_ismapped():
                self.advanced_frame.pack(fill=tk.X, padx=5, pady=5)
            elif not self.advanced_tools_visible and self.advanced_frame.winfo_ismapped():
                self.advanced_frame.pack_forget()

    def show_dashboard(self):
        self.clear_content()
        self.active_panel = "dashboard"
        
        # Header
        header = tk.Label(
            self.content,
            text="🎯 CYBRO WATCHDOG v7.0 - ULTIMATE DASHBOARD",
            font=("Courier New", 20, "bold"),
            bg=self.colors['background'],
            fg=self.colors['primary']
        )
        header.pack(pady=20)
        
        # System status cards
        status_frame = tk.Frame(self.content, bg=self.colors['background'])
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        status_cards = [
            ("🛡️ SECURITY LEVEL", "MAXIMUM", "#00ff9d"),
            ("🔍 ACTIVE MONITORS", "3", "#2196F3"),
            ("⚠️ ACTIVE THREATS", "0", "#FF9800"),
            ("📊 NETWORK DEVICES", str(len(self.network_analyzer.network_devices)), "#9C27B0"),
            ("🤖 AI READINESS", "READY" if LOCAL_AI_AVAILABLE else "OFFLINE", "#4CAF50" if LOCAL_AI_AVAILABLE else "#f44336"),
            ("🌐 NETWORK STATUS", "ONLINE" if self.network_analyzer.gateway_ip else "OFFLINE", "#4CAF50" if self.network_analyzer.gateway_ip else "#f44336"),
            ("👁️ PASSIVE SENSOR", "ONLINE" if self.network_analyzer.passive_sensor_ready else "OFFLINE", "#00ff9d" if self.network_analyzer.passive_sensor_ready else "#f44336")
        ]
        
        for i, (title, value, color) in enumerate(status_cards):
            card = tk.Frame(status_frame, bg=self.colors['surface'], relief='raised', bd=1)
            card.grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky='nsew')
            
            tk.Label(
                card,
                text=title,
                font=("Courier New", 10, "bold"),
                bg=self.colors['surface'],
                fg=self.colors['text_secondary'],
                pady=5
            ).pack(fill=tk.X)
            
            tk.Label(
                card,
                text=value,
                font=("Courier New", 16, "bold"),
                bg=self.colors['surface'],
                fg=color,
                pady=10
            ).pack(fill=tk.X)
            
            status_frame.columnconfigure(i % 3, weight=1)
            status_frame.rowconfigure(i // 3, weight=1)
        
        # Quick actions
        actions_frame = tk.Frame(self.content, bg=self.colors['background'])
        actions_frame.pack(fill=tk.X, padx=20, pady=20)
        
        quick_actions = [
            ("🚀 NETWORK VIEW", self.show_network_analyzer),
            ("📊 ALERT REPORTS", self.show_reports),
            ("🤖 AI CHAT", self.open_ai_chat),
        ]
        if self.advanced_tools_visible:
            quick_actions.extend([
                ("🎭 ANONYMIZER", self.show_anonymizer),
                ("🛡️ PENTEST", self.show_pentest_toolkit),
            ])
        
        for i, (text, command) in enumerate(quick_actions):
            btn = tk.Button(
                actions_frame,
                text=text,
                command=command,
                font=("Courier New", 11, "bold"),
                bg=self.colors['primary'],
                fg=self.colors['background'],
                relief='flat',
                padx=25,
                pady=15
            )
            btn.grid(row=0, column=i, padx=10)
        
        # Features overview
        features_text = """
🎯 ULTIMATE FEATURES v7.0:

🎭 ADVANCED ANONYMIZER
• Real-time PII detection (emails, phones, IPs, MACs, credit cards, SSN, BTC)
• Custom pattern matching with regex support
• Batch file processing
• Comprehensive reporting and statistics

🌐 INTELLIGENT NETWORK ANALYZER  
• Real-time device discovery and monitoring
• ARP scanning with vendor detection
• Packet capture and analysis
• Vulnerability assessment with CVE detection
• Traffic analysis and visualization

🤖 AI-POWERED ANALYZER
• Sentiment analysis for threat assessment
• Advanced threat detection (SQLi, XSS, Command Injection)
• Security posture assessment
• Pattern recognition and analysis
• Predictive analytics

🛡️ PROFESSIONAL PENTEST TOOLKIT
• Automated vulnerability scanning
• Web application security testing
• Wireless security audits
• Network penetration testing
• Comprehensive reporting with remediation guidance

📡 ADVANCED BLE RADAR
• Bluetooth Low Energy device discovery
• Service enumeration and analysis
• Security assessment
• Real-time monitoring and alerts

📊 ENTERPRISE REPORTING SYSTEM
• HTML reports with professional formatting
• Executive summaries and technical details
• Comprehensive security assessments
• Audit trails and compliance reporting
• Custom report generation
        """
        
        features = tk.Label(
            self.content,
            text=features_text,
            font=("Courier New", 11),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            justify=tk.LEFT
        )
        features.pack(pady=20, padx=20)
        
        # Footer
        footer = tk.Label(
            self.content,
            text="🔒 CYBRO WATCHDOG v7.0 - ULTIMATE CYBER SECURITY | USE RESPONSIBLY AND ETHICALLY",
            font=("Courier New", 10),
            bg=self.colors['background'],
            fg=self.colors['text_secondary']
        )
        footer.pack(side=tk.BOTTOM, pady=10)

    def show_anonymizer(self):
        self.active_panel = "anonymizer"
        self.anonymizer.setup_ui(self.content)
    
    def show_network_analyzer(self):
        self.active_panel = "network"
        self.network_analyzer.setup_ui(self.content)
    
    def show_isolation_tester(self):
        self.active_panel = "isolation"
        self.isolation_tester.setup_ui(self.content)
    
    
    def show_bluetooth(self):
        self.active_panel = "bluetooth"
        self.bluetooth_radar.setup_ui(self.content)
    
    def show_pentest_toolkit(self):
        self.active_panel = "pentest"
        self.pentest_toolkit.setup_ui(self.content)
    
    def show_reports(self):
        self.active_panel = "reports"
        self.reporting_system.setup_ui(self.content)
    
    def show_settings(self):
        self.active_panel = "settings"
        self.settings.setup_ui(self.content)

    def _default_ai_chat_model(self) -> str:
        env_model = os.getenv("CYBRO_OLLAMA_MODEL", "").strip()
        if env_model:
            return env_model
        if not EMBEDDED_AI_CHAT_AVAILABLE or get_backend is None:
            return "llama3:latest"
        try:
            backend = get_backend()
            model = getattr(backend, "model", "")
            if getattr(backend, "name", "") == "ollama" and model:
                return model
        except Exception:
            pass
        return "llama3:latest"

    def _refresh_ai_chat_status(self) -> None:
        total_items = len(self.ai_chat_context_paths) + len(self.ai_chat_extra_context_sections)
        self.ai_chat_status_var.set(f"Context: {total_items} items")

    def _get_ai_chat_system_prompt(self) -> str:
        owner_line = (
            " Owner mode is enabled: all devices and networks in scope are owned and authorized."
            if self.ai_chat_owner_mode_var.get()
            else " Owner mode is disabled: stay diagnostic, read-only and do not suggest access actions."
        )
        return AI_CHAT_SYSTEM_PROMPT + owner_line

    def _get_local_network_snapshot(self) -> str:
        def run_command(cmd) -> str:
            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
            except (FileNotFoundError, subprocess.SubprocessError):
                return ""
            output = (completed.stdout or completed.stderr or "").strip()
            return output

        parts = []
        ip_br = run_command(["ip", "-br", "a"])
        if ip_br:
            parts.append("ip -br a:\n" + ip_br)

        ip_route = run_command(["ip", "route"])
        if ip_route:
            parts.append("ip route:\n" + ip_route)

        nmcli_wifi = run_command(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
        if nmcli_wifi:
            active_ssids = [line for line in nmcli_wifi.splitlines() if line.startswith("yes:")]
            parts.append("nmcli active ssid:\n" + ("\n".join(active_ssids) if active_ssids else nmcli_wifi))

        snapshot = "\n\n".join(parts).strip()
        if not snapshot:
            snapshot = "Unavailable. Commands ip -br a, ip route and nmcli did not return usable local network data."
        return snapshot[:2000]

    def _get_device_ips_context(self) -> str:
        if validate_artifact_path is None:
            raise RuntimeError(f"Embedded AI chat unavailable: {embedded_ai_chat_error}")

        db_path = validate_artifact_path("passive_devices.db", allow_db=True)
        query = "SELECT * FROM device_ips ORDER BY rowid DESC LIMIT 50"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in (cursor.description or [])]
        finally:
            conn.close()

        if not rows:
            return "No rows found in passive_devices.db:device_ips"

        lines = []
        for row in reversed(rows):
            lines.append(", ".join(f"{column}={row[column]}" for column in columns))
        return "\n".join(lines)[:4000]

    def _append_ai_chat_transcript(self, speaker: str, text: str) -> None:
        if not self.ai_chat_transcript:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        self.ai_chat_transcript.config(state=tk.NORMAL)
        self.ai_chat_transcript.insert(tk.END, f"[{stamp}] {speaker}: {text}\n\n")
        self.ai_chat_transcript.config(state=tk.DISABLED)
        self.ai_chat_transcript.see(tk.END)

    def _set_ai_chat_busy(self, busy: bool) -> None:
        self.ai_chat_busy = busy
        if self.ai_chat_send_button:
            self.ai_chat_send_button.config(
                state=tk.DISABLED if busy else tk.NORMAL,
                text="Sending..." if busy else "Send",
            )
        self._sync_ai_chat_cloud_controls()

    def _handle_ai_chat_cloud_assist_toggle(self) -> None:
        if not self.ai_chat_cloud_assist_var.get():
            self.ai_chat_cloud_anonymize_override = False
        self._sync_ai_chat_cloud_controls()

    def _handle_ai_chat_anonymize_toggle(self) -> None:
        if not self.ai_chat_cloud_assist_var.get():
            return
        if self.ai_chat_anonymize_before_send_var.get():
            self.ai_chat_cloud_anonymize_override = False
            return
        proceed = messagebox.askyesno(
            "Cloud Assist Safety",
            "Anonymization is OFF. Cloud preview/send may expose sensitive local data.\n\nKeep anonymization OFF?",
        )
        if proceed:
            self.ai_chat_cloud_anonymize_override = True
            self._append_ai_chat_transcript("CONTEXT", "Safety warning acknowledged: Cloud anonymization is OFF.")
        else:
            self.ai_chat_cloud_anonymize_override = False
            self.ai_chat_anonymize_before_send_var.set(True)

    def _handle_ai_chat_cloud_scope_toggle(self) -> None:
        self._enforce_cloud_scope_policy()

    def _hash_text_sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:12]

    def _get_cloud_include_flags(self) -> dict[str, bool]:
        return {
            "snapshot": self.ai_chat_cloud_include_snapshot_var.get(),
            "device_ips": self.ai_chat_cloud_include_device_ips_var.get(),
            "db_overview": self.ai_chat_cloud_include_db_overview_var.get(),
            "reports": self.ai_chat_cloud_include_reports_var.get(),
            "logs": self.ai_chat_cloud_include_logs_var.get(),
            "recent_artifacts": self.ai_chat_cloud_include_recent_artifacts_var.get(),
            "history": self.ai_chat_cloud_include_history_var.get(),
        }

    def _format_cloud_include_flags(self, flags: dict[str, bool] | None = None) -> str:
        active_flags = flags or self._get_cloud_include_flags()
        return ",".join(f"{key}={'1' if value else '0'}" for key, value in active_flags.items())

    def _enforce_cloud_scope_policy(self) -> None:
        if self.ai_chat_send_scope_var.get() == "convo" and not self.ai_chat_cloud_include_history_var.get():
            self.ai_chat_send_scope_var.set("message")
            self._append_ai_chat_transcript(
                "CONTEXT",
                "Cloud scope reverted to message because Conversation scope requires Include history.",
            )

    def _warn_if_cloud_anonymize_off(self, action_name: str) -> bool:
        if self.ai_chat_anonymize_before_send_var.get():
            return True
        return messagebox.askyesno(
            "Cloud Assist Safety",
            f"Anonymization is OFF for {action_name}. Sensitive text may leave this machine.\n\nProceed?",
        )

    def _sync_ai_chat_cloud_controls(self) -> None:
        cloud_enabled = self.ai_chat_cloud_assist_var.get()
        ui_state = tk.DISABLED if self.ai_chat_busy else tk.NORMAL
        cloud_state = tk.NORMAL if cloud_enabled and not self.ai_chat_busy else tk.DISABLED

        if cloud_enabled and not self.ai_chat_anonymize_before_send_var.get() and not self.ai_chat_cloud_anonymize_override:
            self.ai_chat_anonymize_before_send_var.set(True)
            self._append_ai_chat_transcript("CONTEXT", "Safety: Anonymize forced ON when Cloud Assist enabled.")
        if not cloud_enabled:
            self.ai_chat_cloud_anonymize_override = False
        self._enforce_cloud_scope_policy()

        if self.ai_chat_anonymize_check:
            self.ai_chat_anonymize_check.config(state=cloud_state if cloud_enabled else tk.DISABLED)
        if self.ai_chat_scope_message_radio:
            self.ai_chat_scope_message_radio.config(state=cloud_state)
        if self.ai_chat_scope_convo_radio:
            self.ai_chat_scope_convo_radio.config(state=cloud_state)
        if self.ai_chat_cloud_model_entry:
            self.ai_chat_cloud_model_entry.config(state=cloud_state)
        for control in self.ai_chat_cloud_whitelist_controls:
            control.config(state=cloud_state)
        if self.ai_chat_preview_button:
            self.ai_chat_preview_button.config(state=cloud_state)
        if self.ai_chat_cloud_send_button:
            self.ai_chat_cloud_send_button.config(state=cloud_state)
        if self.ai_chat_send_button:
            self.ai_chat_send_button.config(state=ui_state if not self.ai_chat_busy else tk.DISABLED)

    def _cloud_scope_label(self) -> str:
        return "convo" if self.ai_chat_send_scope_var.get() == "convo" else "message"

    def _collect_ai_chat_context_sections(self, context_paths) -> tuple[list[tuple[str, str, str]], list[tuple[str, int]]]:
        sections = []
        files_read = []

        local_snapshot = self._get_local_network_snapshot()
        sections.append(("local_network_snapshot", local_snapshot, "snapshot"))
        files_read.append(("local_network_snapshot", len(local_snapshot.encode("utf-8", errors="ignore"))))

        for title, text in self.ai_chat_extra_context_sections.items():
            if title == "device_ips_last_50":
                section_type = "device_ips"
            elif title == "manual_local_snapshot":
                section_type = "snapshot"
            else:
                section_type = "extra"
            sections.append((title, text, section_type))
            files_read.append((title, len(text.encode("utf-8", errors="ignore"))))

        try:
            recent_artifacts = list_recent_artifacts(limit=8) if list_recent_artifacts else []
        except Exception:
            recent_artifacts = []
        if recent_artifacts:
            artifact_text = "\n".join(
                f"- {item['path']} | modified={item['modified']} | size={item['size']}"
                for item in recent_artifacts
            )
            sections.append(("recent_artifacts", artifact_text, "recent_artifacts"))
            files_read.append(("recent_artifacts", len(artifact_text.encode("utf-8", errors="ignore"))))

        for item in context_paths:
            path = validate_artifact_path(item, allow_db=True) if validate_artifact_path else None
            if not path:
                continue
            relative = str(path.relative_to(PROJECT_ROOT))
            if path.suffix.lower() == ".db":
                text = json.dumps(sqlite_table_overview(path), ensure_ascii=False, indent=2) if sqlite_table_overview else ""
                section_type = "db_overview"
            elif path.suffix.lower() == ".log" or "cybro_logs" in path.parts:
                text = tail_text_file(path, lines=200) if tail_text_file else ""
                section_type = "logs"
            elif "security_reports" in path.parts:
                text = read_text_file(path, max_bytes=15_000) if read_text_file else ""
                section_type = "reports"
            else:
                text = read_text_file(path, max_bytes=15_000) if read_text_file else ""
                section_type = "extra"
            sections.append((relative, text, section_type))
            files_read.append((relative, len(text.encode("utf-8", errors="ignore"))))

        return sections, files_read

    def _render_context_sections(self, sections, max_chars: int) -> tuple[str, list[tuple[str, int]]]:
        chunks = []
        used = []
        remaining = max_chars
        for title, text, _section_type in sections:
            if remaining <= 0:
                break
            header = f"### {title}\n"
            budget = max(0, remaining - len(header) - 1)
            clipped = text[:budget]
            section = f"{header}{clipped}\n"
            chunks.append(section)
            used.append((title, len(clipped.encode("utf-8", errors="ignore"))))
            remaining -= len(section)
        if not chunks:
            return "No CYBRO artifacts selected.", used
        return "\n".join(chunks), used

    def _build_cloud_context_text(self, context_paths) -> tuple[str, dict[str, bool]]:
        sections, _files_read = self._collect_ai_chat_context_sections(context_paths)
        flags = self._get_cloud_include_flags()
        filtered = []
        for title, text, section_type in sections:
            if section_type == "snapshot" and flags["snapshot"]:
                filtered.append((title, text, section_type))
            elif section_type == "device_ips" and flags["device_ips"]:
                filtered.append((title, text, section_type))
            elif section_type == "db_overview" and flags["db_overview"]:
                filtered.append((title, text, section_type))
            elif section_type == "reports" and flags["reports"]:
                filtered.append((title, text, section_type))
            elif section_type == "logs" and flags["logs"]:
                filtered.append((title, text, section_type))
            elif section_type == "recent_artifacts" and flags["recent_artifacts"]:
                filtered.append((title, text, section_type))

        ordered_types = ["snapshot", "device_ips", "db_overview", "recent_artifacts", "reports", "logs"]
        ordered_sections = []
        for section_type in ordered_types:
            ordered_sections.extend([item for item in filtered if item[2] == section_type])
        context_text, _used = self._render_context_sections(ordered_sections, AI_CHAT_MAX_CONTEXT_CHARS)
        return context_text, flags

    def _build_cloud_payload(self, prompt: str, history_snapshot, context_text: str) -> str:
        flags = self._get_cloud_include_flags()
        owner_mode = "enabled" if self.ai_chat_owner_mode_var.get() else "disabled"
        policy_header = (
            "CLOUD POLICY HEADER:\n"
            f"Authorized owner environment. owner_mode={owner_mode}.\n"
            "Never request exploitation, only diagnostics and configuration guidance.\n"
            "MAC != IP, never confuse.\n"
            "If data missing, ask for minimal additional context.\n\n"
        )
        system_text = "SYSTEM:\n" + self._get_ai_chat_system_prompt() + "\n\n"
        user_text = f"USER PROMPT:\n{prompt}\n"

        history_text = ""
        if self.ai_chat_send_scope_var.get() == "convo" and flags["history"] and history_snapshot:
            history_lines = ["CONVERSATION HISTORY:"]
            for item in history_snapshot[-AI_CHAT_MAX_HISTORY_MESSAGES:]:
                role = str(item.get("role", "user")).upper()
                content = str(item.get("content", ""))
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines) + "\n\n"

        base_text = policy_header + system_text + user_text
        if history_text:
            base_text += history_text
        max_chars = 50_000
        remaining = max(0, max_chars - len(base_text) - len("LOCAL CONTEXT:\n\n"))
        clipped_context = context_text[:remaining]
        payload = policy_header + system_text + "LOCAL CONTEXT:\n" + clipped_context + "\n\n" + user_text
        if history_text:
            payload += "\n" + history_text
        return payload[:max_chars]

    def _anonymize_for_cloud(self, text: str) -> tuple[str, dict]:
        from anonymizer_core import anonymize_payload

        anonymized_text, report, _mapping = anonymize_payload(text, mode="cloud")
        return anonymized_text, report

    def _show_cloud_preview_window(self, preview_text: str, report: dict, anonymized: bool, model_name: str, scope: str, preview_hash: str, flags_text: str) -> None:
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Cloud Payload Preview")
        preview_window.geometry("900x700")
        preview_window.configure(bg=self.colors['background'])

        tk.Label(
            preview_window,
            text="What will be sent",
            font=("Courier New", 14, "bold"),
            bg=self.colors['background'],
            fg=self.colors['primary'],
        ).pack(anchor="w", padx=12, pady=(12, 6))

        summary = (
            f"model={model_name}\n"
            f"scope={scope}\n"
            f"anonymized={'YES' if anonymized else 'NO'}\n"
            f"chars={len(preview_text)}\n"
            f"hash={preview_hash}\n"
            f"include_flags={flags_text}\n"
            f"mode={report.get('mode', 'none')}\n"
            f"replacements={report.get('replacements', 0)}\n"
            f"unique_mappings={report.get('unique_mappings', 0)}\n"
            f"stats_keys={', '.join(report.get('pattern_catalog', [])[:12]) or 'none'}"
        )
        if not anonymized:
            summary += "\nwarning=Anonymization OFF"

        summary_box = scrolledtext.ScrolledText(
            preview_window,
            height=6,
            wrap=tk.WORD,
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            relief='flat',
        )
        summary_box.pack(fill=tk.X, padx=12, pady=(0, 8))
        summary_box.insert("1.0", summary)
        summary_box.config(state=tk.DISABLED)

        preview_box = scrolledtext.ScrolledText(
            preview_window,
            wrap=tk.WORD,
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            relief='flat',
        )
        preview_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        preview_box.insert("1.0", preview_text)
        preview_box.config(state=tk.DISABLED)

    def _prompt_cloud_send_token(self, preview_hash: str) -> bool:
        result = {"confirmed": False}
        expected = f"SEND-{preview_hash}"

        dialog = tk.Toplevel(self.root)
        dialog.title("Confirm Cloud Send")
        dialog.geometry("420x180")
        dialog.configure(bg=self.colors['background'])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"Type {expected} to confirm",
            font=("Courier New", 10, "bold"),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
        ).pack(padx=12, pady=(16, 8))

        entry = tk.Entry(
            dialog,
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        )
        entry.pack(fill=tk.X, padx=12, pady=(0, 12), ipady=6)
        entry.focus_set()

        feedback = tk.Label(
            dialog,
            text="",
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg="#ff6b6b",
        )
        feedback.pack(padx=12, pady=(0, 8))

        def confirm() -> None:
            if entry.get().strip() == expected:
                result["confirmed"] = True
                dialog.destroy()
            else:
                feedback.config(text="Confirmation token mismatch.")

        tk.Button(
            dialog,
            text="Confirm",
            command=confirm,
            font=("Courier New", 9, "bold"),
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            padx=12,
            pady=6,
        ).pack(pady=(0, 12))

        dialog.wait_window()
        return result["confirmed"]

    def _ensure_voice_cache_dir(self) -> Path:
        cache_dir = PROJECT_ROOT / "voice_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _hash_file_sha256(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()[:12]

    def _get_wav_duration_seconds(self, file_path: Path) -> float:
        try:
            with wave.open(str(file_path), "rb") as wav_file:
                frame_rate = wav_file.getframerate() or 1
                return round(wav_file.getnframes() / float(frame_rate), 2)
        except Exception:
            return 0.0

    def _sync_voice_button_mode(self, *_args) -> None:
        if not self.ai_chat_voice_button:
            return
        self.ai_chat_voice_button.unbind("<ButtonPress-1>")
        self.ai_chat_voice_button.unbind("<ButtonRelease-1>")
        if self.voice_mode_var.get() == "ptt":
            self.ai_chat_voice_button.config(command=lambda: None, text="🎙 hold")
            self.ai_chat_voice_button.bind("<ButtonPress-1>", self._on_voice_press)
            self.ai_chat_voice_button.bind("<ButtonRelease-1>", self._on_voice_release)
        else:
            self.ai_chat_voice_button.config(command=self._toggle_voice_record, text="🎙 click")
        if self.voice_recording:
            self.ai_chat_voice_button.config(text="■ REC")

    def _record_voice_start(self) -> None:
        if self.voice_recording:
            return
        cache_dir = self._ensure_voice_cache_dir()
        output_file = cache_dir / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        try:
            proc = subprocess.Popen(
                ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", str(output_file)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            self.notification_system.add_notification("AI Chat Voice", f"Voice start failed: {exc}", 'warning', 7000)
            return

        self.voice_proc = proc
        self.voice_recording = True
        self.voice_last_file = str(output_file)
        if self.ai_chat_voice_button:
            self.ai_chat_voice_button.config(text="■ REC")
        self.notification_system.add_notification("AI Chat Voice", f"Recording started ({self.voice_mode_var.get().upper()})", 'info', 2500)

    def _prompt_voice_token(self, preview_hash: str) -> bool:
        result = {"confirmed": False}
        expected = f"SEND-{preview_hash}"
        file_path = Path(self.voice_last_file) if self.voice_last_file else None
        bytes_count = file_path.stat().st_size if file_path and file_path.exists() else 0
        seconds = self._get_wav_duration_seconds(file_path) if file_path and file_path.exists() else 0.0
        mode_name = self.voice_mode_var.get()

        dialog = tk.Toplevel(self.root)
        dialog.title("Confirm Voice Placeholder")
        dialog.geometry("560x280")
        dialog.configure(bg=self.colors['background'])
        dialog.transient(self.root)
        dialog.grab_set()

        summary = (
            f"file={file_path}\n"
            f"bytes={bytes_count}\n"
            f"seconds={seconds:.2f}\n"
            f"hash={preview_hash}\n"
            f"include_flags=voice_only\n"
            f"mode={mode_name}"
        )

        tk.Label(
            dialog,
            text="Paranoid local voice preview",
            font=("Courier New", 10, "bold"),
            bg=self.colors['background'],
            fg=self.colors['primary'],
        ).pack(anchor="w", padx=12, pady=(14, 8))

        summary_box = scrolledtext.ScrolledText(
            dialog,
            height=7,
            wrap=tk.WORD,
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            relief='flat',
        )
        summary_box.pack(fill=tk.X, padx=12, pady=(0, 10))
        summary_box.insert("1.0", summary)
        summary_box.config(state=tk.DISABLED)

        tk.Label(
            dialog,
            text=f"Type {expected} to confirm",
            font=("Courier New", 10, "bold"),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
        ).pack(padx=12, pady=(0, 8))

        entry = tk.Entry(
            dialog,
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        )
        entry.pack(fill=tk.X, padx=12, pady=(0, 10), ipady=6)
        entry.focus_set()

        feedback = tk.Label(
            dialog,
            text="",
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg="#ff6b6b",
        )
        feedback.pack(padx=12, pady=(0, 8))

        def confirm() -> None:
            if entry.get().strip() == expected:
                result["confirmed"] = True
                dialog.destroy()
            else:
                feedback.config(text="Confirmation token mismatch.")

        tk.Button(
            dialog,
            text="Confirm",
            command=confirm,
            font=("Courier New", 9, "bold"),
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            padx=12,
            pady=6,
        ).pack(pady=(0, 12))

        dialog.wait_window()
        return result["confirmed"]

    def _record_voice_stop(self) -> None:
        if not self.voice_recording:
            return

        proc = self.voice_proc
        self.voice_recording = False
        self.voice_proc = None
        if self.ai_chat_voice_button:
            self._sync_voice_button_mode()

        if proc:
            try:
                proc.send_signal(signal.SIGINT)
            except Exception:
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass

        file_path = Path(self.voice_last_file) if self.voice_last_file else None
        if not file_path or not file_path.exists():
            self.notification_system.add_notification("AI Chat Voice", "No local WAV file was created.", 'warning', 7000)
            return

        bytes_count = file_path.stat().st_size
        if bytes_count <= 0:
            self.notification_system.add_notification("AI Chat Voice", "Recorded WAV is empty.", 'warning', 7000)
            return

        seconds = self._get_wav_duration_seconds(file_path)
        preview_hash = self._hash_file_sha256(file_path)
        self._append_ai_chat_transcript("SYSTEM", f"VOICE recorded: bytes={bytes_count}, seconds={seconds:.2f}, hash={preview_hash}")

        if not self._prompt_voice_token(preview_hash):
            self.notification_system.add_notification("AI Chat Voice", "Voice placeholder cancelled.", 'info', 5000)
            return

        if not self.ai_chat_input:
            return

        placeholder = f"[VOICE_READY] file={file_path} hash={preview_hash} mode={self.voice_mode_var.get()}"
        current_text = self.ai_chat_input.get().strip()
        new_text = f"{current_text} {placeholder}".strip() if current_text else placeholder
        self.ai_chat_input.delete(0, tk.END)
        self.ai_chat_input.insert(0, new_text)
        self.ai_chat_input.focus_force()

    def _toggle_voice_record(self) -> None:
        if self.voice_recording:
            self._record_voice_stop()
        else:
            self._record_voice_start()

    def _on_voice_press(self, event=None):
        if self.voice_mode_var.get() != "ptt":
            return None
        self._record_voice_start()
        return "break"

    def _on_voice_release(self, event=None):
        if self.voice_mode_var.get() != "ptt":
            return None
        self._record_voice_stop()
        return "break"

    def preview_ai_chat_cloud_payload(self) -> None:
        if not self.ai_chat_cloud_assist_var.get():
            self.notification_system.add_notification("Cloud Assist", "Enable Cloud Assist before preview.", 'warning', 6000)
            return
        if not self.ai_chat_input:
            return
        self._enforce_cloud_scope_policy()

        prompt = self.ai_chat_input.get().strip()
        if not prompt:
            self.notification_system.add_notification("Cloud Assist", "Enter a message before preview.", 'warning', 6000)
            return
        if not self._warn_if_cloud_anonymize_off("preview"):
            return

        history_snapshot = self.ai_chat_history[-AI_CHAT_MAX_HISTORY_MESSAGES:]
        context_snapshot = sorted(self.ai_chat_context_paths)
        context_text, flags = self._build_cloud_context_text(context_snapshot)
        payload_text = self._build_cloud_payload(prompt, history_snapshot, context_text)
        anonymized = self.ai_chat_anonymize_before_send_var.get()
        if anonymized:
            preview_text, report = self._anonymize_for_cloud(payload_text)
        else:
            preview_text = payload_text
            report = {
                "mode": "none",
                "replacements": 0,
                "unique_mappings": 0,
                "pattern_catalog": [],
            }

        scope = self._cloud_scope_label()
        model_name = self.ai_chat_cloud_model_var.get().strip() or "gpt-5"
        preview_hash = self._hash_text_sha256(preview_text)
        flags_text = self._format_cloud_include_flags(flags)
        self.ai_chat_last_cloud_preview_text = preview_text
        self.ai_chat_last_cloud_preview_timestamp = time.time()
        self.ai_chat_last_cloud_preview_hash = preview_hash
        self.ai_chat_last_cloud_preview_chars = len(preview_text)
        self.ai_chat_last_cloud_preview_flags = flags
        self.ai_chat_last_cloud_preview_meta = {
            "model": model_name,
            "scope": scope,
            "anonymized": anonymized,
            "chars": len(preview_text),
            "hash": preview_hash,
            "flags": flags_text,
        }
        self._show_cloud_preview_window(preview_text, report, anonymized, model_name, scope, preview_hash, flags_text)
        self._append_ai_chat_transcript(
            "CONTEXT",
            f"Cloud preview ready: hash={preview_hash}, chars={len(preview_text)}, anonymized={'YES' if anonymized else 'NO'}, flags={flags_text}",
        )
        _append_ai_chat_audit(
            "cloud_preview",
            [("cloud_payload", len(preview_text.encode('utf-8', errors='ignore')))],
            note=f"model={model_name};scope={scope};anonymized={anonymized};hash={preview_hash};include_flags={flags_text}",
        )

    def send_ai_chat_to_cloud(self) -> None:
        if not self.ai_chat_cloud_assist_var.get():
            self.notification_system.add_notification("Cloud Assist", "Enable Cloud Assist before sending.", 'warning', 6000)
            return
        self._enforce_cloud_scope_policy()
        if self.ai_chat_busy:
            return
        if not self.ai_chat_last_cloud_preview_text or (time.time() - self.ai_chat_last_cloud_preview_timestamp) > 30:
            self.notification_system.add_notification("Cloud Assist", "Generate a fresh preview before sending.", 'warning', 7000)
            return
        if not self._warn_if_cloud_anonymize_off("send"):
            return

        preview_text = self.ai_chat_last_cloud_preview_text
        meta = dict(self.ai_chat_last_cloud_preview_meta)
        model_name = str(meta.get("model") or self.ai_chat_cloud_model_var.get().strip() or "gpt-5")
        scope = str(meta.get("scope") or self._cloud_scope_label())
        anonymized = bool(meta.get("anonymized"))
        preview_hash = self._hash_text_sha256(preview_text)
        if preview_hash != self.ai_chat_last_cloud_preview_hash:
            self.notification_system.add_notification("Cloud Assist", "Preview hash mismatch. Generate a new preview.", 'warning', 7000)
            return
        flags_text = str(meta.get("flags") or self._format_cloud_include_flags(self.ai_chat_last_cloud_preview_flags))
        confirm = messagebox.askyesno(
            "Confirm Cloud Send",
            f"model={model_name}\nscope={scope}\nanonymized={anonymized}\nchars={len(preview_text)}\nhash={preview_hash}\ninclude_flags={flags_text}\n\nSend exactly this preview text to cloud?",
        )
        if not confirm:
            return
        if not self._prompt_cloud_send_token(preview_hash):
            self.notification_system.add_notification("Cloud Assist", "Cloud send cancelled: confirmation token mismatch.", 'warning', 7000)
            return
        self._set_ai_chat_busy(True)

        def worker() -> None:
            try:
                from cloud_backend_openai import send_openai_responses

                response = send_openai_responses(preview_text, model_name, timeout=60)
                self.root.after(
                    0,
                    lambda: self._finish_cloud_ai_chat_success(response, model_name, scope, anonymized, len(preview_text), preview_hash, flags_text),
                )
            except Exception as exc:
                self.root.after(0, lambda: self._finish_cloud_ai_chat_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_chat_close(self) -> None:
        if self.voice_recording and self.voice_proc:
            try:
                self.voice_proc.send_signal(signal.SIGINT)
            except Exception:
                pass
            try:
                self.voice_proc.wait(timeout=1)
            except Exception:
                try:
                    self.voice_proc.terminate()
                except Exception:
                    pass
            self.voice_recording = False
            self.voice_proc = None
        if self.ai_chat_window:
            self.ai_chat_window.destroy()
        self.ai_chat_window = None
        self.ai_chat_transcript = None
        self.ai_chat_input = None
        self.ai_chat_send_button = None
        self.ai_chat_preview_button = None
        self.ai_chat_cloud_send_button = None
        self.ai_chat_anonymize_check = None
        self.ai_chat_scope_message_radio = None
        self.ai_chat_scope_convo_radio = None
        self.ai_chat_cloud_model_entry = None
        self.ai_chat_cloud_whitelist_controls = []
        self.ai_chat_voice_mode_menu = None
        self.ai_chat_voice_button = None
        self.ai_chat_voice_auto_send_check = None

    def open_ai_chat(self) -> None:
        if self.ai_chat_window and self.ai_chat_window.winfo_exists():
            self.ai_chat_window.deiconify()
            self.ai_chat_window.lift()
            self.ai_chat_window.focus_force()
            return

        self.ai_chat_window = tk.Toplevel(self.root)
        self.ai_chat_window.title("CYBRO AI Chat")
        self.ai_chat_window.geometry("980x720")
        self.ai_chat_window.configure(bg=self.colors['background'])
        self.ai_chat_window.protocol("WM_DELETE_WINDOW", self._on_ai_chat_close)

        header = tk.Frame(self.ai_chat_window, bg=self.colors['surface'])
        header.pack(fill=tk.X, padx=10, pady=(10, 6))

        tk.Label(
            header,
            text="CYBRO AI Chat",
            font=("Courier New", 14, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['primary'],
        ).pack(side=tk.LEFT, padx=12, pady=10)

        tk.Label(
            header,
            text="Model",
            font=("Courier New", 10, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
        ).pack(side=tk.LEFT, padx=(20, 6))

        tk.Entry(
            header,
            textvariable=self.ai_chat_model_var,
            width=24,
            font=("Courier New", 10),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        ).pack(side=tk.LEFT, padx=(0, 12), pady=10)

        tk.Checkbutton(
            header,
            text="Owner mode",
            variable=self.ai_chat_owner_mode_var,
            font=("Courier New", 9, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['background'],
            activebackground=self.colors['surface'],
            activeforeground=self.colors['text_primary'],
        ).pack(side=tk.LEFT, padx=(0, 12), pady=10)

        tk.Checkbutton(
            header,
            text="Cloud Assist",
            variable=self.ai_chat_cloud_assist_var,
            command=self._handle_ai_chat_cloud_assist_toggle,
            font=("Courier New", 9, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['background'],
            activebackground=self.colors['surface'],
            activeforeground=self.colors['text_primary'],
        ).pack(side=tk.LEFT, padx=(0, 12), pady=10)

        tk.Label(
            header,
            textvariable=self.ai_chat_status_var,
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary'],
        ).pack(side=tk.RIGHT, padx=12)

        controls = tk.Frame(self.ai_chat_window, bg=self.colors['background'])
        controls.pack(fill=tk.X, padx=10, pady=(0, 6))

        control_buttons = [
            ("Clear chat", self.clear_ai_chat),
            ("Add local snapshot", self.add_ai_chat_local_snapshot),
            ("Add latest log", self.add_ai_chat_latest_log),
            ("Add latest report", self.add_ai_chat_latest_report),
            ("Add IPs from DB", self.add_ai_chat_device_ips),
            ("DB overview", self.add_ai_chat_db_overview),
        ]
        for text, command in control_buttons:
            tk.Button(
                controls,
                text=text,
                command=command,
                font=("Courier New", 9),
                bg=self.colors['surface'],
                fg=self.colors['text_primary'],
                relief='flat',
                padx=12,
                pady=8,
            ).pack(side=tk.LEFT, padx=(0, 6))

        cloud_controls = tk.Frame(self.ai_chat_window, bg=self.colors['background'])
        cloud_controls.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.ai_chat_anonymize_check = tk.Checkbutton(
            cloud_controls,
            text="Anonymize before sending",
            variable=self.ai_chat_anonymize_before_send_var,
            command=self._handle_ai_chat_anonymize_toggle,
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['surface'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['text_primary'],
        )
        self.ai_chat_anonymize_check.pack(side=tk.LEFT, padx=(0, 10))

        self.ai_chat_scope_message_radio = tk.Radiobutton(
            cloud_controls,
            text="This message only",
            variable=self.ai_chat_send_scope_var,
            value="message",
            command=self._handle_ai_chat_cloud_scope_toggle,
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['surface'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['text_primary'],
        )
        self.ai_chat_scope_message_radio.pack(side=tk.LEFT, padx=(0, 8))

        self.ai_chat_scope_convo_radio = tk.Radiobutton(
            cloud_controls,
            text=f"Conversation (last {AI_CHAT_MAX_HISTORY_MESSAGES})",
            variable=self.ai_chat_send_scope_var,
            value="convo",
            command=self._handle_ai_chat_cloud_scope_toggle,
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['surface'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['text_primary'],
        )
        self.ai_chat_scope_convo_radio.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            cloud_controls,
            text="Cloud model",
            font=("Courier New", 9, "bold"),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
        ).pack(side=tk.LEFT, padx=(10, 6))

        self.ai_chat_cloud_model_entry = tk.Entry(
            cloud_controls,
            textvariable=self.ai_chat_cloud_model_var,
            width=14,
            font=("Courier New", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        )
        self.ai_chat_cloud_model_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.ai_chat_preview_button = tk.Button(
            cloud_controls,
            text="Preview payload",
            command=self.preview_ai_chat_cloud_payload,
            font=("Courier New", 9, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            relief='flat',
            padx=12,
            pady=6,
        )
        self.ai_chat_preview_button.pack(side=tk.LEFT, padx=(4, 6))

        self.ai_chat_cloud_send_button = tk.Button(
            cloud_controls,
            text="Send to Cloud",
            command=self.send_ai_chat_to_cloud,
            font=("Courier New", 9, "bold"),
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            padx=12,
            pady=6,
        )
        self.ai_chat_cloud_send_button.pack(side=tk.LEFT)

        whitelist_frame = tk.Frame(self.ai_chat_window, bg=self.colors['background'])
        whitelist_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        tk.Label(
            whitelist_frame,
            text="CLOUD WHITELIST",
            font=("Courier New", 9, "bold"),
            bg=self.colors['background'],
            fg=self.colors['primary'],
        ).pack(side=tk.LEFT, padx=(0, 10))

        whitelist_specs = [
            ("Snapshot", self.ai_chat_cloud_include_snapshot_var),
            ("Device IPs", self.ai_chat_cloud_include_device_ips_var),
            ("DB overview", self.ai_chat_cloud_include_db_overview_var),
            ("Reports", self.ai_chat_cloud_include_reports_var),
            ("Logs", self.ai_chat_cloud_include_logs_var),
            ("Recent artifacts", self.ai_chat_cloud_include_recent_artifacts_var),
            ("History", self.ai_chat_cloud_include_history_var),
        ]
        for text, variable in whitelist_specs:
            btn = tk.Checkbutton(
                whitelist_frame,
                text=text,
                variable=variable,
                command=self._handle_ai_chat_cloud_scope_toggle,
                font=("Courier New", 8),
                bg=self.colors['background'],
                fg=self.colors['text_primary'],
                selectcolor=self.colors['surface'],
                activebackground=self.colors['background'],
                activeforeground=self.colors['text_primary'],
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self.ai_chat_cloud_whitelist_controls.append(btn)

        self.ai_chat_transcript = scrolledtext.ScrolledText(
            self.ai_chat_window,
            wrap=tk.WORD,
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        )
        self.ai_chat_transcript.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.ai_chat_transcript.config(state=tk.DISABLED)

        input_row = tk.Frame(self.ai_chat_window, bg=self.colors['background'])
        input_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.ai_chat_input = tk.Entry(
            input_row,
            font=("Courier New", 10),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
        )
        self.ai_chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=8)
        self.ai_chat_input.bind("<Return>", self.send_ai_chat_message)

        self.ai_chat_send_button = tk.Button(
            input_row,
            text="Send",
            command=self.send_ai_chat_message,
            font=("Courier New", 10, "bold"),
            bg=self.colors['primary'],
            fg=self.colors['background'],
            relief='flat',
            padx=18,
            pady=8,
        )
        self.ai_chat_send_button.pack(side=tk.RIGHT)

        voice_controls = tk.Frame(input_row, bg=self.colors['background'])
        voice_controls.pack(side=tk.RIGHT, padx=(0, 8))

        tk.Label(
            voice_controls,
            text="Voice mode",
            font=("Courier New", 9, "bold"),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.ai_chat_voice_mode_menu = tk.OptionMenu(
            voice_controls,
            self.voice_mode_var,
            "ptt",
            "ptt",
            "click",
            command=self._sync_voice_button_mode,
        )
        self.ai_chat_voice_mode_menu.config(
            font=("Courier New", 9, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            activebackground=self.colors['surface'],
            activeforeground=self.colors['text_primary'],
            highlightthickness=0,
            relief='flat',
        )
        self.ai_chat_voice_mode_menu["menu"].config(
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            activebackground=self.colors['accent'],
            activeforeground='white',
        )
        self.ai_chat_voice_mode_menu.pack(side=tk.LEFT, padx=(0, 8))

        self.ai_chat_voice_button = tk.Button(
            voice_controls,
            text="🎙",
            font=("Courier New", 10, "bold"),
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            padx=12,
            pady=8,
        )
        self.ai_chat_voice_button.pack(side=tk.LEFT, padx=(0, 8))

        self.ai_chat_voice_auto_send_check = tk.Checkbutton(
            voice_controls,
            text="Auto-send after stop",
            variable=self.voice_auto_send_var,
            font=("Courier New", 9),
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['surface'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['text_primary'],
        )
        self.ai_chat_voice_auto_send_check.pack(side=tk.LEFT)
        self._sync_voice_button_mode()

        self._refresh_ai_chat_status()
        self._sync_ai_chat_cloud_controls()
        self._append_ai_chat_transcript("SYSTEM", self._get_ai_chat_system_prompt())
        if not EMBEDDED_AI_CHAT_AVAILABLE:
            self._append_ai_chat_transcript("SYSTEM", f"Embedded AI chat unavailable: {embedded_ai_chat_error}")
            return
        try:
            recent = list_recent_artifacts(limit=5)
        except Exception as exc:
            recent = []
            self._append_ai_chat_transcript("SYSTEM", f"Recent artifacts unavailable: {exc}")
        if recent:
            lines = [f"- {item['path']} ({item['modified']})" for item in recent]
            self._append_ai_chat_transcript("SYSTEM", "Recent CYBRO artifacts:\n" + "\n".join(lines))

    def clear_ai_chat(self) -> None:
        self.ai_chat_history.clear()
        self.ai_chat_context_paths.clear()
        self.ai_chat_extra_context_sections.clear()
        self.ai_chat_last_cloud_preview_text = ""
        self.ai_chat_last_cloud_preview_timestamp = 0.0
        self.ai_chat_last_cloud_preview_meta = {}
        self.ai_chat_last_cloud_preview_hash = ""
        self.ai_chat_last_cloud_preview_chars = 0
        self.ai_chat_last_cloud_preview_flags = {}
        self.ai_chat_cloud_anonymize_override = False
        self._refresh_ai_chat_status()
        if self.ai_chat_transcript:
            self.ai_chat_transcript.config(state=tk.NORMAL)
            self.ai_chat_transcript.delete("1.0", tk.END)
            self.ai_chat_transcript.config(state=tk.DISABLED)
        self._append_ai_chat_transcript("SYSTEM", "Chat history and selected CYBRO context cleared.")

    def _add_ai_chat_context_path(self, relative_path: str, preview_text: str, audit_action: str) -> None:
        if not EMBEDDED_AI_CHAT_AVAILABLE or validate_artifact_path is None:
            raise RuntimeError(f"Embedded AI chat unavailable: {embedded_ai_chat_error}")
        path = validate_artifact_path(relative_path, allow_db=True)
        relative = str(path.relative_to(PROJECT_ROOT))
        self.ai_chat_context_paths.add(relative)
        self._refresh_ai_chat_status()
        self._append_ai_chat_transcript("CONTEXT", f"Added {relative}\n{preview_text[:1200]}")
        _append_ai_chat_audit(
            audit_action,
            [(relative, len(preview_text.encode('utf-8', errors='ignore')))],
            note="manual_context_add",
        )

    def add_ai_chat_latest_log(self) -> None:
        try:
            artifacts = list_recent_artifacts(limit=20) if list_recent_artifacts else []
            candidate = "cybro_logs/cybro.log"
            if not artifacts:
                artifacts = []
            if not any(item.get("path") == candidate for item in artifacts):
                log_candidates = [item.get("path") for item in artifacts if str(item.get("path", "")).endswith(".log")]
                if log_candidates:
                    candidate = log_candidates[0]
            preview = tail_text_file(candidate, lines=60) if tail_text_file else ""
            self._add_ai_chat_context_path(candidate, preview or "[Empty log]", "tail_log")
        except Exception as exc:
            self.notification_system.add_notification("AI Chat", f"Latest log unavailable: {exc}", 'warning', 7000)

    def add_ai_chat_latest_report(self) -> None:
        try:
            reports = list_reports(limit=1) if list_reports else []
            if not reports:
                raise FileNotFoundError("No reports found in security_reports/")
            candidate = reports[0]["path"]
            preview = read_text_file(candidate, max_bytes=2500) if read_text_file else ""
            self._add_ai_chat_context_path(candidate, preview or "[Empty report]", "add_report")
        except Exception as exc:
            self.notification_system.add_notification("AI Chat", f"Latest report unavailable: {exc}", 'warning', 7000)

    def add_ai_chat_device_ips(self) -> None:
        try:
            device_ips_text = self._get_device_ips_context()
            self.ai_chat_extra_context_sections["device_ips_last_50"] = device_ips_text
            self._refresh_ai_chat_status()
            self._append_ai_chat_transcript("CONTEXT", f"Added device IPs from DB\n{device_ips_text[:1500]}")
            _append_ai_chat_audit(
                "add_device_ips",
                [("passive_devices.db:device_ips", len(device_ips_text.encode('utf-8', errors='ignore')))],
                note="manual_context_add",
            )
        except Exception as exc:
            self.notification_system.add_notification("AI Chat", f"Add IPs from DB failed: {exc}", 'warning', 7000)

    def add_ai_chat_local_snapshot(self) -> None:
        try:
            local_snapshot = self._get_local_network_snapshot()
            self.ai_chat_extra_context_sections["manual_local_snapshot"] = local_snapshot
            self._refresh_ai_chat_status()
            self._append_ai_chat_transcript("CONTEXT", f"Added local network snapshot\n{local_snapshot}")
            _append_ai_chat_audit(
                "add_local_snapshot",
                [("local_network_snapshot", len(local_snapshot.encode('utf-8', errors='ignore')))],
                note="manual_context_add",
            )
        except Exception as exc:
            self.notification_system.add_notification("AI Chat", f"Add local snapshot failed: {exc}", 'warning', 7000)

    def add_ai_chat_db_overview(self) -> None:
        added = []
        try:
            for db_name in ("passive_devices.db", "cybro_watchdog.db"):
                try:
                    path = validate_artifact_path(db_name, allow_db=True) if validate_artifact_path else None
                    if not path:
                        continue
                    overview = sqlite_table_overview(path) if sqlite_table_overview else {}
                    relative = str(path.relative_to(PROJECT_ROOT))
                    self.ai_chat_context_paths.add(relative)
                    added.append(relative)
                    preview = json.dumps(overview, ensure_ascii=False, indent=2)[:1500]
                    self._append_ai_chat_transcript("CONTEXT", f"Added DB overview for {relative}\n{preview}")
                except FileNotFoundError:
                    continue
            if not added:
                raise FileNotFoundError("No allowed CYBRO database found")
            self._refresh_ai_chat_status()
            _append_ai_chat_audit("db_overview", [(path, 0) for path in added], note="manual_context_add")
        except Exception as exc:
            self.notification_system.add_notification("AI Chat", f"DB overview unavailable: {exc}", 'warning', 7000)

    def _build_ai_chat_context(self, context_paths) -> tuple[str, list[tuple[str, int]]]:
        sections, _files_read = self._collect_ai_chat_context_sections(context_paths)
        return self._render_context_sections(sections, AI_CHAT_MAX_CONTEXT_CHARS)

    def send_ai_chat_message(self, event=None) -> None:
        if event is not None:
            try:
                event.widget
            except AttributeError:
                pass
        if self.ai_chat_busy or not self.ai_chat_input:
            return
        if not EMBEDDED_AI_CHAT_AVAILABLE or get_backend is None:
            self.notification_system.add_notification("AI Chat", f"Embedded AI chat unavailable: {embedded_ai_chat_error}", 'warning', 7000)
            return

        prompt = self.ai_chat_input.get().strip()
        if not prompt:
            return

        model_name = self.ai_chat_model_var.get().strip() or self._default_ai_chat_model()
        history_snapshot = self.ai_chat_history[-AI_CHAT_MAX_HISTORY_MESSAGES:]
        context_snapshot = sorted(self.ai_chat_context_paths)
        self.ai_chat_input.delete(0, tk.END)
        self._append_ai_chat_transcript("USER", prompt)
        self._set_ai_chat_busy(True)

        def worker() -> None:
            try:
                context_text, files_read = self._build_ai_chat_context(context_snapshot)
                backend = get_backend()
                if hasattr(backend, "model"):
                    backend.model = model_name
                messages = [
                    {"role": "system", "content": self._get_ai_chat_system_prompt()},
                    {"role": "system", "content": f"CYBRO context:\n{context_text}"},
                ]
                messages.extend(history_snapshot)
                messages.append({"role": "user", "content": prompt})
                response = backend.chat(messages, timeout=300)
                self.root.after(
                    0,
                    lambda: self._finish_ai_chat_success(prompt, response, files_read, model_name, len(context_snapshot)),
                )
            except Exception as exc:
                self.root.after(0, lambda: self._finish_ai_chat_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_ai_chat_success(self, prompt: str, response: str, files_read, model_name: str, context_items: int) -> None:
        self.ai_chat_history.extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        )
        self.ai_chat_history = self.ai_chat_history[-AI_CHAT_MAX_HISTORY_MESSAGES:]
        self._append_ai_chat_transcript("AI", response)
        self._set_ai_chat_busy(False)
        _append_ai_chat_audit(
            "chat",
            files_read,
            note=f"model={model_name};context_items={context_items}",
        )

    def _finish_cloud_ai_chat_success(self, response: str, model_name: str, scope: str, anonymized: bool, char_count: int, preview_hash: str, flags_text: str) -> None:
        self._append_ai_chat_transcript("AI-CLOUD", response)
        self._set_ai_chat_busy(False)
        _append_ai_chat_audit(
            "cloud_send",
            [("cloud_payload", char_count)],
            note=f"model={model_name};scope={scope};anonymized={anonymized};hash={preview_hash};include_flags={flags_text}",
        )

    def _finish_cloud_ai_chat_error(self, error_text: str) -> None:
        self._append_ai_chat_transcript("AI-CLOUD", f"Request failed: {error_text}")
        self._set_ai_chat_busy(False)

    def _finish_ai_chat_error(self, error_text: str) -> None:
        self._append_ai_chat_transcript("AI", f"Request failed: {error_text}")
        self._set_ai_chat_busy(False)

    def _wifi_monitor_button_text(self) -> str:
        if self._wifi_toggle_in_progress:
            return "Switching..."
        return "Disable Monitor Mode" if self.wifi_monitor_enabled else "Enable Monitor Mode"

    def update_wifi_monitor_button(self) -> None:
        if self.wifi_monitor_button:
            self.wifi_monitor_button.config(
                text=self._wifi_monitor_button_text(),
                state=tk.DISABLED if self._wifi_toggle_in_progress else tk.NORMAL,
            )

    def toggle_wifi_monitor_mode(self):
        if self._wifi_toggle_in_progress:
            return
        self._wifi_toggle_in_progress = True
        self.update_wifi_monitor_button()
        threading.Thread(target=self._wifi_monitor_worker, daemon=True).start()

    def _wifi_monitor_worker(self):
        try:
            if not self.wifi_monitor_enabled:
                self._enable_wifi_monitor_mode()
            else:
                self._disable_wifi_monitor_mode()
        finally:
            self._wifi_toggle_in_progress = False
            self.root.after(0, self.update_wifi_monitor_button)

    def _enable_wifi_monitor_mode(self) -> None:
        interface = self._select_wifi_interface()
        if not interface:
            self.notification_system.add_notification(
                "Wi-Fi Monitor Mode",
                "No suitable Wi-Fi interface found for monitor mode.",
                'warning'
            )
            return
        if self._run_wifi_command(["sudo", "airmon-ng", "start", interface]):
            self.wifi_monitor_interface = interface
            self.wifi_monitor_enabled = True
            self.notification_system.add_notification(
                "Wi-Fi Monitor Mode",
                "Wi-Fi adapter switched to monitor mode. Internet access may be unavailable.",
                'info'
            )
            return
        success = (
            self._run_wifi_command(["sudo", "ip", "link", "set", interface, "down"], ignore_errors=True)
            and self._run_wifi_command(["sudo", "iw", interface, "set", "monitor", "none"], ignore_errors=True)
            and self._run_wifi_command(["sudo", "ip", "link", "set", interface, "up"], ignore_errors=True)
        )
        if success:
            self.wifi_monitor_interface = interface
            self.wifi_monitor_enabled = True
            self.notification_system.add_notification(
                "Wi-Fi Monitor Mode",
                "Wi-Fi adapter switched to monitor mode. Internet access may be unavailable.",
                'info'
            )
        else:
            self.notification_system.add_notification(
                "Wi-Fi Monitor Mode",
                "Failed to enable monitor mode on selected adapter.",
                'warning'
            )

    def _disable_wifi_monitor_mode(self) -> None:
        interface = self.wifi_monitor_interface
        if not interface:
            self.notification_system.add_notification(
                "Wi-Fi Monitor Mode",
                "No monitor interface to restore.",
                'warning'
            )
            return
        mon_iface = f"{interface}mon"
        self._run_wifi_command(["sudo", "airmon-ng", "stop", mon_iface], ignore_errors=True)
        self._run_wifi_command(["sudo", "airmon-ng", "stop", interface], ignore_errors=True)
        self._run_wifi_command(["sudo", "ip", "link", "set", interface, "down"], ignore_errors=True)
        self._run_wifi_command(["sudo", "iw", "dev", interface, "set", "type", "managed"], ignore_errors=True)
        self._run_wifi_command(["sudo", "ip", "link", "set", interface, "up"], ignore_errors=True)
        self._run_wifi_command(["sudo", "systemctl", "restart", "NetworkManager"], ignore_errors=True)
        self.wifi_monitor_enabled = False
        self.wifi_monitor_interface = None
        self.notification_system.add_notification(
            "Wi-Fi Monitor Mode",
            "Wi-Fi adapter restored to managed mode.",
            'success'
        )

    def _select_wifi_interface(self) -> Optional[str]:
        interfaces = self._detect_wifi_interfaces()
        if not interfaces:
            return None
        preferred = [iface for iface in interfaces if iface != "wlan0"] or interfaces
        return preferred[0]

    def _detect_wifi_interfaces(self) -> list[str]:
        try:
            output = subprocess.check_output(["ip", "-o", "link", "show"], text=True)
        except subprocess.CalledProcessError:
            return []
        interfaces = []
        for line in output.splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2:
                name = parts[1].strip()
                if name.startswith("wl"):
                    interfaces.append(name)
        return interfaces

    def _run_wifi_command(self, cmd, ignore_errors: bool = False) -> bool:
        if (
            sys.platform != "win32"
            and os.geteuid() != 0
            and isinstance(cmd, list)
            and len(cmd) >= 2
            and cmd[0] == "sudo"
        ):
            tool = cmd[1]
            manual_cmd = " ".join(cmd)
            self.notification_system.add_notification(
                "Requires sudo",
                f"Requires sudo: {tool}. Run manually: {manual_cmd}",
                'warning',
                9000
            )
            return False
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False if not ignore_errors else False
    
    def run(self):
        self.root.mainloop()

def main():
    print("🔷 CYBRO WatchDog v7.0 - Ultimate Cyber Security Suite")
    print("🚀 Initializing systems...")
    
    # ASCII art banner
    banner = r"""
┌──────────────────────────────────────────────┐
│                                              │
│   ██████╗ ██╗   ██╗██████╗ ██████╗  ██████╗  │
│  ██╔════╝ ╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗ │
│  ██║       ╚████╔╝ ██████╔╝██████╔╝██║   ██║ │
│  ██║        ╚██╔╝  ██╔══██╗██╔══██╗██║   ██║ │
│  ╚██████╗    ██║   ██████╔╝██║  ██║╚██████╔╝ │
│   ╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  │
│                                              │
└──────────────────────────────────────────────┘
"""
    
    print(banner)
    print("🔧 Loading modules...")
    
    # Check dependencies
    dependencies = {
        'Local AI Analyst': LOCAL_AI_AVAILABLE,
        'Network Analysis': SCAPY_AVAILABLE,
        'Bluetooth Radar': BLE_AVAILABLE,
        'OCR Capabilities': OCR_AVAILABLE
    }

    for feature, available in dependencies.items():
        status = "✅ AVAILABLE" if available else "❌ NOT AVAILABLE"
        print(f"   {feature}: {status}")
    
    print("\n🚀 Starting CYBRO WatchDog...")
    
    try:
        app = UltimateCyberpunkGUI()
        print("✅ System initialized successfully!")
        print("💡 Use responsibly and ethically.")
        app.run()
    except Exception as e:
        print(f"❌ Critical error during initialization: {e}")
        traceback.print_exc()
        print("\n🔧 Troubleshooting tips:")
        print("   • Run with sudo for full network functionality")
        print("   • Install missing dependencies: pip install scapy bleak transformers torch")
        print("   • Check system permissions")


# Hlavný spustiteľný kód
if __name__ == "__main__":
    main()
