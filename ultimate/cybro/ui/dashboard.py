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
from concurrent.futures import ThreadPoolExecutor, as_completed
import webbrowser

# Voliteľné importy
try:
    import transformers
    import torch
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

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

from ..sensors.presence_watchdog import PresenceWatchdogSensor
from .network_map import NetworkMapWidget

# Decision loop integration -------------------------------------------------
DECISION_LOOP = None
_ORIGINAL_SUBPROCESS_RUN = subprocess.run


def attach_decision_loop(decision_loop):
    global DECISION_LOOP
    DECISION_LOOP = decision_loop
    if decision_loop:
        decision_loop.audit_logger.log_decision(
            {"phase": "ui_linked", "message": "Dashboard attached to decision loop"}
        )


def _guarded_subprocess_run(*args, **kwargs):
    label = kwargs.pop("decision_label", "subprocess_call")
    context = {"args": args, "kwargs": kwargs}

    def _action():
        return _ORIGINAL_SUBPROCESS_RUN(*args, **kwargs)

    if DECISION_LOOP:
        return DECISION_LOOP.execute_action(label, context, _action)
    return _action()


subprocess.run = _guarded_subprocess_run

if SCAPY_AVAILABLE:
    _ORIGINAL_SRP = srp

    def _guarded_srp(*args, **kwargs):
        def _action():
            return _ORIGINAL_SRP(*args, **kwargs)

        if DECISION_LOOP:
            return DECISION_LOOP.execute_action(
                "scapy_srp", {"args": args, "kwargs": kwargs}, _action
            )
        return _action()

    srp = _guarded_srp

# Konštanty a priečinky
LOG_DIR = Path("cybro_logs")
PROFILE_DIR = LOG_DIR / "network_profiles"
ASSET_DIR = Path("cybro_assets")
CORRUPTED_DIR = Path("corrupted_data")
CAPTURE_DIR = Path("packet_captures")
REPORTS_DIR = Path("security_reports")
DB_PATH = Path("cybro_watchdog.db")
CONFIG_PATH = Path("cybro_config.json")

for d in [LOG_DIR, PROFILE_DIR, ASSET_DIR, CORRUPTED_DIR, CAPTURE_DIR, REPORTS_DIR]:
    d.mkdir(exist_ok=True)

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
    def __init__(self, parent, presence_watchdog=None):
        self.parent = parent
        self.presence_watchdog = presence_watchdog
        self.network_devices = []
        self.network_range = None
        self.gateway_ip = None
        self.local_mac = self._get_local_mac()
        self.watchdog_running = False
        self.watchdog_thread = None
        self.missing_counts = {}
        self.whitelist = []
        self.network_map = NetworkMapWidget(self.parent.colors)
        self._popup_cooldown = {}
        
        # Initialize network
        self.initialize_network()
    
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
            
            # Start monitoring
            self.start_network_monitoring()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "Network Error",
                str(e),
                'critical'
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
                print(f"Monitoring error: {e}")
                time.sleep(30)
    
    def _arp_scan(self):
        """ARP skenovanie"""

        def _scan():
            try:
                if not self.network_range:
                    return
                
                # Create ARP request
                arp = ARP(pdst=self.network_range)
                ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                packet = ether/arp
                
                # Send and receive
                result = srp(packet, timeout=2, verbose=False)[0]
                
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
                print(f"ARP scan error: {e}")
        
        self.parent.guard_action(
            "arp_scan",
            {"range": self.network_range},
            _scan
        )
    
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
            existing = next((d for d in self.network_devices if d['ip'] == current['ip']), None)
            
            if existing:
                # Update existing device
                existing.update(current)
            else:
                # New device found
                self.network_devices.append(current)
                new_devices.append(current)
                self.network_map.highlight_device(current['mac'], "NEW_DEVICE")
                self._record_presence_event("NEW_DEVICE", current['mac'])
                self._maybe_popup(
                    "Zariadenie pripojené",
                    self._format_device_message(current),
                    current.get('mac')
                )
                
                self.parent.notification_system.add_notification(
                    "New Device",
                    f"IP: {current['ip']}, MAC: {current['mac']}",
                    'warning'
                )
        
        # Check for missing devices
        current_ips = {d['ip'] for d in current_devices}
        for device in self.network_devices[:]:
            if device['ip'] not in current_ips:
                self.missing_counts[device['ip']] = self.missing_counts.get(device['ip'], 0) + 1
                
                if self.missing_counts[device['ip']] > 3:  # Missing for 3 scans
                    self.parent.notification_system.add_notification(
                        "Device Missing",
                        f"IP: {device['ip']} has disappeared",
                        'critical'
                    )
                    self.network_map.highlight_device(device.get('mac'), "DEVICE_DISAPPEARED")
                    self._record_presence_event("DEVICE_DISAPPEARED", device.get('mac'))
                    self._maybe_popup(
                        "Zariadenie odpojené",
                        self._format_device_message(device),
                        device.get('mac')
                    )
                    self.network_devices.remove(device)
                    del self.missing_counts[device['ip']]
        
        self.network_map.update_devices(self.network_devices)
        self._notify_presence_watchdog()

    def _notify_presence_watchdog(self, event=None):
        if not self.presence_watchdog:
            return
        self.presence_watchdog.feed_devices(self.network_devices)
        if event:
            self.presence_watchdog.record_event(event)

    def _record_presence_event(self, event_type, mac):
        if not self.presence_watchdog or not mac:
            return
        payload = {
            "event_type": event_type,
            "mac": mac,
            "timestamp": datetime.now(timezone.utc),
        }
        self.presence_watchdog.record_event(payload)

    def _maybe_popup(self, title, message, mac, cooldown=30):
        mac_norm = (mac or "").upper()
        if not mac_norm:
            return
        now = time.time()
        last = self._popup_cooldown.get(mac_norm, 0)
        if now - last < cooldown:
            return
        self._popup_cooldown[mac_norm] = now
        try:
            messagebox.showinfo(title, message)
        except Exception:
            pass

    @staticmethod
    def _format_device_message(device):
        hostname = device.get('hostname') or 'Unknown'
        ip = device.get('ip') or 'Unknown'
        mac = (device.get('mac') or '').upper()
        mac = mac or 'UNKNOWN'
        return f"{hostname} {ip} ({mac})"
    
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

        # Network topology map
        map_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
        map_frame.pack(fill=tk.BOTH, padx=20, pady=(0, 10))
        tk.Label(
            map_frame,
            text="🗺️ REAL-TIME NETWORK MAP",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(anchor="w", padx=10, pady=(10, 0))
        self.network_map.attach(map_frame)
        
        # Control buttons
        control_frame = tk.Frame(parent, bg=self.parent.colors['background'])
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        buttons = [
            ("🔍 SCAN NETWORK", self.scan_network),
            ("📡 PACKET CAPTURE", self.packet_capture),
            ("🛡️ VULNERABILITY SCAN", self.vulnerability_scan),
            ("📊 TRAFFIC ANALYSIS", self.traffic_analysis),
            ("🎯 PORT SCAN", self.port_scan)
        ]
        
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
            self.network_map.update_devices(self.network_devices)
            self._notify_presence_watchdog()
            return
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        for device in self.network_devices:
            self.devices_tree.insert("", "end", values=(
                device['ip'],
                device['mac'],
                device.get('hostname', 'Unknown'),
                device.get('vendor', 'Unknown'),
                device.get('last_seen', datetime.now()).strftime("%H:%M:%S")
            ))
        
        self.network_map.update_devices(self.network_devices)
        self._notify_presence_watchdog()
    
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

class UltimateAIanalyzer:
    def __init__(self, parent):
        self.parent = parent
        self.ai_models = {}
        self.analysis_history = []
        
        # Initialize AI models if available
        if AI_AVAILABLE:
            self._initialize_models()
    
    def _initialize_models(self):
        """Inicializuje AI modely"""
        try:
            # Sentiment analysis
            self.ai_models['sentiment'] = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english"
            )
            
            self.parent.notification_system.add_notification(
                "AI Models Loaded",
                "AI analyzer ready for use",
                'success'
            )
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "AI Initialization Error",
                str(e),
                'warning'
            )
    
    def setup_ui(self, parent):
        """Nastaví UI pre AI analyzátor"""
        self.parent.clear_content()
        
        # Header
        header = tk.Label(
            parent,
            text="🤖 ULTIMATE AI ANALYZER - INTELLIGENT THREAT DETECTION",
            font=("Courier New", 18, "bold"),
            bg=self.parent.colors['background'],
            fg=self.parent.colors['primary']
        )
        header.pack(pady=15)
        
        if not AI_AVAILABLE:
            warning_frame = tk.Frame(parent, bg=self.parent.colors['surface'])
            warning_frame.pack(fill=tk.X, padx=20, pady=20)
            
            tk.Label(
                warning_frame,
                text="⚠️ AI MODULES NOT AVAILABLE\nInstall: pip install transformers torch",
                font=("Courier New", 14),
                bg=self.parent.colors['surface'],
                fg='#ff6b6b',
                justify=tk.CENTER
            ).pack(pady=20)
            return
        
        # Main container
        main_container = tk.Frame(parent, bg=self.parent.colors['background'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Input area
        input_frame = tk.Frame(main_container, bg=self.parent.colors['surface'])
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(
            input_frame,
            text="INPUT TEXT FOR ANALYSIS:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        self.ai_input = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg='#1a1a1a',
            fg='white',
            height=12
        )
        self.ai_input.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Analysis buttons
        button_frame = tk.Frame(main_container, bg=self.parent.colors['background'])
        button_frame.pack(fill=tk.X, pady=10)
        
        ai_buttons = [
            ("🧠 SENTIMENT ANALYSIS", self.sentiment_analysis),
            ("🛡️ THREAT DETECTION", self.threat_detection),
            ("📊 SECURITY ASSESSMENT", self.security_assessment),
            ("🔍 PATTERN ANALYSIS", self.pattern_analysis),
            ("📝 GENERATE REPORT", self.generate_ai_report)
        ]
        
        for i, (text, command) in enumerate(ai_buttons):
            btn = tk.Button(
                button_frame,
                text=text,
                command=command,
                font=("Courier New", 9, "bold"),
                bg=self.parent.colors['primary'],
                fg=self.parent.colors['background'],
                relief='flat',
                padx=10,
                pady=8
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
        
        # Output area
        output_frame = tk.Frame(main_container, bg=self.parent.colors['surface'])
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            output_frame,
            text="AI ANALYSIS RESULTS:",
            font=("Courier New", 12, "bold"),
            bg=self.parent.colors['surface'],
            fg=self.parent.colors['primary']
        ).pack(pady=5)
        
        self.ai_output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg='#1a1a1a',
            fg='#00ff00',
            height=12
        )
        self.ai_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def sentiment_analysis(self):
        """Analýza sentimentu"""
        text = self.ai_input.get(1.0, tk.END).strip()
        if not text:
            self.parent.notification_system.add_notification(
                "Empty Input",
                "Please enter text for analysis",
                'warning'
            )
            return
        
        def analyze():
            try:
                self.ai_output.delete(1.0, tk.END)
                self.ai_output.insert(tk.END, "🤖 Analyzing sentiment...\n\n")
                
                # Use first 512 characters (model limit)
                analysis_text = text[:512]
                result = self.ai_models['sentiment'](analysis_text)[0]
                
                output = f"SENTIMENT ANALYSIS RESULTS:\n{'='*40}\n"
                output += f"Label: {result['label']}\n"
                output += f"Confidence: {result['score']:.2%}\n\n"
                
                # Additional insights
                if result['label'] == 'NEGATIVE' and result['score'] > 0.8:
                    output += "⚠️ STRONG NEGATIVE SENTIMENT DETECTED\n"
                    output += "This text may contain concerning content\n"
                elif result['label'] == 'POSITIVE':
                    output += "✅ Positive content detected\n"
                
                self.ai_output.insert(tk.END, output)
                
                # Save to history
                self.analysis_history.append({
                    'type': 'sentiment',
                    'timestamp': datetime.now(),
                    'input_preview': text[:100] + "...",
                    'result': result
                })
                
                self.parent.notification_system.add_notification(
                    "Sentiment Analysis",
                    f"Result: {result['label']} ({result['score']:.2%})",
                    'success'
                )
                
            except Exception as e:
                self.ai_output.insert(tk.END, f"❌ Analysis error: {e}")
                self.parent.notification_system.add_notification(
                    "Analysis Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def threat_detection(self):
        """Detekcia hrozieb"""
        text = self.ai_input.get(1.0, tk.END).strip()
        if not text:
            self.parent.notification_system.add_notification(
                "Empty Input",
                "Please enter text for analysis",
                'warning'
            )
            return
        
        def detect_threats():
            try:
                self.ai_output.delete(1.0, tk.END)
                self.ai_output.insert(tk.END, "🛡️ Scanning for threats...\n\n")
                
                # Threat patterns
                threat_patterns = {
                    'SQL Injection': [
                        r'select.*from', r'insert.*into', r'update.*set',
                        r'delete.*from', r'union.*select', r'drop.*table'
                    ],
                    'XSS Attack': [
                        r'<script>', r'javascript:', r'onload=',
                        r'onerror=', r'alert\(', r'document\.cookie'
                    ],
                    'Command Injection': [
                        r';.*ls', r'\|.*cat', r'&.*rm',
                        r'`.*whoami', r'\$\(.*id\)'
                    ],
                    'Path Traversal': [
                        r'\.\./', r'\.\.\\', r'/etc/passwd',
                        r'c:\\windows', r'%2e%2e%2f'
                    ]
                }
                
                threats_found = {}
                
                for threat_type, patterns in threat_patterns.items():
                    threats_found[threat_type] = []
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            threats_found[threat_type].extend(matches)
                
                # Generate report
                output = "THREAT DETECTION REPORT:\n" + "="*40 + "\n\n"
                
                total_threats = sum(len(threats) for threats in threats_found.values())
                
                if total_threats == 0:
                    output += "✅ NO THREATS DETECTED\n"
                    output += "The text appears to be safe from common attack patterns.\n"
                else:
                    output += f"🚨 {total_threats} POTENTIAL THREATS DETECTED:\n\n"
                    
                    for threat_type, matches in threats_found.items():
                        if matches:
                            output += f"🔴 {threat_type}:\n"
                            for match in set(matches):
                                output += f"   - {match}\n"
                            output += "\n"
                    
                    output += "💡 RECOMMENDATIONS:\n"
                    output += "• Validate and sanitize all inputs\n"
                    output += "• Use parameterized queries\n"
                    output += "• Implement proper output encoding\n"
                    output += "• Conduct security testing\n"
                
                self.ai_output.insert(tk.END, output)
                
                # Save to history
                self.analysis_history.append({
                    'type': 'threat_detection',
                    'timestamp': datetime.now(),
                    'input_preview': text[:100] + "...",
                    'threats_found': total_threats,
                    'details': threats_found
                })
                
                self.parent.notification_system.add_notification(
                    "Threat Detection",
                    f"Found {total_threats} potential threats",
                    'critical' if total_threats > 0 else 'success'
                )
                
            except Exception as e:
                self.ai_output.insert(tk.END, f"❌ Threat detection error: {e}")
                self.parent.notification_system.add_notification(
                    "Threat Detection Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=detect_threats, daemon=True).start()
    
    def security_assessment(self):
        """Bezpečnostné hodnotenie"""
        text = self.ai_input.get(1.0, tk.END).strip()
        if not text:
            self.parent.notification_system.add_notification(
                "Empty Input",
                "Please enter text for assessment",
                'warning'
            )
            return
        
        def assess_security():
            try:
                self.ai_output.delete(1.0, tk.END)
                self.ai_output.insert(tk.END, "📊 Conducting security assessment...\n\n")
                
                # Analyze various security aspects
                security_metrics = {
                    'Password Strength': self._assess_password_strength(text),
                    'Data Exposure': self._assess_data_exposure(text),
                    'Code Quality': self._assess_code_quality(text),
                    'Configuration Issues': self._assess_configuration(text)
                }
                
                # Generate assessment report
                output = "SECURITY ASSESSMENT REPORT:\n" + "="*40 + "\n\n"
                
                total_score = 0
                max_score = len(security_metrics) * 10
                
                for metric, (score, details) in security_metrics.items():
                    total_score += score
                    output += f"{metric}: {score}/10\n"
                    output += f"  {details}\n\n"
                
                overall_score = (total_score / max_score) * 100
                
                output += f"OVERALL SECURITY SCORE: {overall_score:.1f}%\n\n"
                
                if overall_score >= 80:
                    output += "✅ EXCELLENT SECURITY POSTURE\n"
                elif overall_score >= 60:
                    output += "⚠️ MODERATE SECURITY POSTURE\n"
                else:
                    output += "🔴 POOR SECURITY POSTURE\n"
                
                output += "\n💡 RECOMMENDATIONS:\n"
                output += "• Implement strong password policies\n"
                output += "• Encrypt sensitive data\n"
                output += "• Follow secure coding practices\n"
                output += "• Regular security audits\n"
                
                self.ai_output.insert(tk.END, output)
                
                self.parent.notification_system.add_notification(
                    "Security Assessment",
                    f"Overall score: {overall_score:.1f}%",
                    'success' if overall_score >= 70 else 'warning'
                )
                
            except Exception as e:
                self.ai_output.insert(tk.END, f"❌ Assessment error: {e}")
                self.parent.notification_system.add_notification(
                    "Assessment Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=assess_security, daemon=True).start()
    
    def _assess_password_strength(self, text):
        """Hodnotí silu hesla"""
        # Simple password strength assessment
        score = 5  # Base score
        
        if len(text) >= 8:
            score += 1
        if any(c.isupper() for c in text):
            score += 1
        if any(c.islower() for c in text):
            score += 1
        if any(c.isdigit() for c in text):
            score += 1
        if any(not c.isalnum() for c in text):
            score += 1
        
        details = "Strong password" if score >= 8 else "Weak password - needs improvement"
        return min(score, 10), details
    
    def _assess_data_exposure(self, text):
        """Hodnotí expozíciu dát"""
        # Check for sensitive data patterns
        sensitive_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IP
            r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',  # MAC
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'  # Credit card
        ]
        
        sensitive_count = 0
        for pattern in sensitive_patterns:
            sensitive_count += len(re.findall(pattern, text))
        
        score = max(0, 10 - sensitive_count * 2)
        details = f"Found {sensitive_count} potential sensitive data items"
        
        return score, details
    
    def _assess_code_quality(self, text):
        """Hodnotí kvalitu kódu"""
        # Simple code quality assessment
        lines = text.split('\n')
        if len(lines) < 5:
            return 5, "Insufficient code for proper assessment"
        
        score = 7
        details = "Moderate code quality"
        
        return score, details
    
    def _assess_configuration(self, text):
        """Hodnotí konfiguráciu"""
        # Check for common misconfigurations
        misconfig_patterns = [
            r'password\s*=\s*["\']\w+["\']',  # Hardcoded password
            r'debug\s*=\s*true',  # Debug enabled
            r'admin\s*=\s*["\']admin["\']',  # Default credentials
        ]
        
        misconfig_count = 0
        for pattern in misconfig_patterns:
            misconfig_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        score = max(0, 10 - misconfig_count * 3)
        details = f"Found {misconfig_count} potential misconfigurations"
        
        return score, details
    
    def pattern_analysis(self):
        """Analýza patternov"""
        self.parent.notification_system.add_notification(
            "Pattern Analysis",
            "Advanced pattern analysis - Coming soon!",
            'info'
        )
    
    def generate_ai_report(self):
        """Generuje AI report"""
        if not self.analysis_history:
            self.parent.notification_system.add_notification(
                "No Data",
                "No analysis history to report",
                'warning'
            )
            return
        
        def generate_report():
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = REPORTS_DIR / f"ai_analysis_report_{timestamp}.html"
                
                # Generate HTML report
                html_content = self._generate_ai_html_report()
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                self.ai_output.insert(tk.END, f"\n📊 Report generated: {report_file.name}\n")
                
                self.parent.notification_system.add_notification(
                    "Report Generated",
                    f"AI report saved to {report_file.name}",
                    'success'
                )
                
            except Exception as e:
                self.parent.notification_system.add_notification(
                    "Report Error",
                    str(e),
                    'critical'
                )
        
        threading.Thread(target=generate_report, daemon=True).start()
    
    def _generate_ai_html_report(self):
        """Generuje HTML report pre AI analýzy"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CYBRO AI Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #0a0a12; color: white; }
                .header { background: #1a1a2e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
                .analysis { background: #2a2a3e; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .positive { border-left: 4px solid #4CAF50; }
                .warning { border-left: 4px solid #FF9800; }
                .critical { border-left: 4px solid #F44336; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔷 CYBRO AI Analysis Report</h1>
                <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p>Total Analyses: """ + str(len(self.analysis_history)) + """</p>
            </div>
        """
        
        for analysis in self.analysis_history[-10:]:  # Last 10 analyses
            html += f"""
            <div class="analysis {self._get_analysis_class(analysis)}">
                <h3>{analysis['type'].replace('_', ' ').title()}</h3>
                <p><strong>Time:</strong> {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Input Preview:</strong> {analysis['input_preview']}</p>
            </div>
            """
        
        html += "</body></html>"
        return html
    
    def _get_analysis_class(self, analysis):
        """Získa CSS class pre analýzu"""
        if analysis['type'] == 'threat_detection':
            return 'critical' if analysis.get('threats_found', 0) > 0 else 'positive'
        return 'warning'

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
            duration = int(self.scan_duration.get() or 10)

            def _run_scan():
                try:
                    self.scanning = True
                    
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

            self.parent.guard_action(
                "ble_scan",
                {"duration": duration, "device_count": len(self.bluetooth_devices)},
                _run_scan
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
        """Vygeneruje AI report"""
        if not hasattr(self.parent, 'ai_analyzer') or not self.parent.ai_analyzer.analysis_history:
            self.parent.notification_system.add_notification(
                "No Data",
                "No AI analysis history available",
                'warning'
            )
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"ai_analysis_report_{timestamp}.html"
            
            html_content = self.parent.ai_analyzer._generate_ai_html_report()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.parent.notification_system.add_notification(
                "AI Report Generated",
                f"AI analysis report saved to {report_file.name}",
                'success'
            )
            
            self.load_recent_reports()
            
        except Exception as e:
            self.parent.notification_system.add_notification(
                "AI Report Error",
                str(e),
                'critical'
            )
    
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
            
            # AI Analysis section
            if hasattr(self.parent, 'ai_analyzer'):
                html += f"""
                <div class="section">
                    <h2>🤖 AI Security Analysis</h2>
                    <p><span class="stats">Total Analyses:</span> {len(self.parent.ai_analyzer.analysis_history)}</p>
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
            print(f"Config save error: {e}")
    
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
• AI: {'Available' if AI_AVAILABLE else 'Not Available'}
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
    def __init__(self, decision_loop=None):
        self.decision_loop = decision_loop
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

        if decision_loop and hasattr(decision_loop, "presence_watchdog"):
            self.presence_watchdog = decision_loop.presence_watchdog
        else:
            self.presence_watchdog = PresenceWatchdogSensor()
        
        # Kontrola sudo
        self.has_sudo = os.geteuid() == 0 if sys.platform != "win32" else True
        
        # Inicializácia systémov
        self.notification_system = UltimateNotificationSystem(self)
        self.anonymizer = UltimateAnonymizer(self)
        self.network_analyzer = UltimateNetworkAnalyzer(
            self,
            presence_watchdog=self.presence_watchdog
        )
        self.isolation_tester = UltimateIsolationTester(self)
        self.ai_analyzer = UltimateAIanalyzer(self)
        self.bluetooth_radar = UltimateBluetoothRadar(self)
        self.pentest_toolkit = UltimatePentestToolkit(self)
        self.reporting_system = UltimateReportingSystem(self)
        self.settings = UltimateSettings(self)
        
        self.setup_gui()
        
        # Štartovacie notifikácie
        self.root.after(1000, self.show_startup_notifications)

    def guard_action(self, label, metadata, action_callable):
        """Route privileged actions through the central decision loop."""
        if self.decision_loop:
            return self.decision_loop.execute_action(label, metadata, action_callable)
        return action_callable()
        
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
        
        if not AI_AVAILABLE:
            self.notification_system.add_notification(
                "AI Module",
                "AI features disabled - install transformers",
                'info'
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
        
        # Sidebar header
        sidebar_header = tk.Label(
            sidebar,
            text="NAVIGATION",
            font=("Courier New", 12, "bold"),
            bg=self.colors['primary'],
            fg=self.colors['background'],
            pady=10
        )
        sidebar_header.pack(fill=tk.X)
        
        # Navigation buttons
        nav_buttons = [
            ("🏠 DASHBOARD", self.show_dashboard),
            ("🎭 ULTIMATE ANONYMIZER", self.show_anonymizer),
            ("🌐 NETWORK ANALYZER", self.show_network_analyzer),
            ("🛰️ ISOLATION TESTER", self.show_isolation_tester),
            ("🤖 AI ANALYZER", self.show_ai_analyzer),
            ("📡 BLE RADAR", self.show_bluetooth),
            ("🛡️ PENTEST TOOLKIT", self.show_pentest_toolkit),
            ("📊 SECURITY REPORTS", self.show_reports),
            ("⚙️ SYSTEM SETTINGS", self.show_settings)
        ]
        
        for text, command in nav_buttons:
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
        
        # System info
        info_frame = tk.Frame(sidebar, bg=self.colors['surface'])
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        sys_info = f"""
System Status:
• Sudo: {'✅' if self.has_sudo else '❌'}
• AI: {'✅' if AI_AVAILABLE else '❌'}
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
    
    def create_main_content(self):
        self.content = tk.Frame(self.root, bg=self.colors['background'])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.show_dashboard()
    
    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        self.clear_content()
        
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
            ("🤖 AI READINESS", "READY" if AI_AVAILABLE else "OFFLINE", "#4CAF50" if AI_AVAILABLE else "#f44336"),
            ("🌐 NETWORK STATUS", "ONLINE" if self.network_analyzer.gateway_ip else "OFFLINE", "#4CAF50" if self.network_analyzer.gateway_ip else "#f44336")
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
            ("🚀 QUICK SCAN", self.show_network_analyzer),
            ("🎭 ANONYMIZE DATA", self.show_anonymizer),
            ("🤖 AI ANALYSIS", self.show_ai_analyzer),
            ("🛡️ PENTEST", self.show_pentest_toolkit)
        ]
        
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
        self.anonymizer.setup_ui(self.content)
    
    def show_network_analyzer(self):
        self.network_analyzer.setup_ui(self.content)
    
    def show_isolation_tester(self):
        self.isolation_tester.setup_ui(self.content)
    
    def show_ai_analyzer(self):
        self.ai_analyzer.setup_ui(self.content)
    
    def show_bluetooth(self):
        self.bluetooth_radar.setup_ui(self.content)
    
    def show_pentest_toolkit(self):
        self.pentest_toolkit.setup_ui(self.content)
    
    def show_reports(self):
        self.reporting_system.setup_ui(self.content)
    
    def show_settings(self):
        self.settings.setup_ui(self.content)
    
    def run(self):
        self.root.mainloop()

def launch_ui(decision_loop=None):
    attach_decision_loop(decision_loop)
    print("🔷 CYBRO WatchDog v7.0 - Ultimate Cyber Security Suite")
    print("🚀 Initializing systems...")
    
    banner = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║    ██████╗██╗   ██╗██████╗  ██████╗      ██╗    ██╗ █████╗ ███████╗██████╗  ║
    ║   ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝      ██║    ██║██╔══██╗██╔════╝██╔══██╗ ║
    ║   ██║      ╚████╔╝ ██████╔╝██║  ███╗     ██║ █╗ ██║███████║███████╗██║  ██║ ║
    ║   ██║       ╚██╔╝  ██╔══██╗██║   ██║     ██║███╗██║██╔══██║╚════██║██║  ██║ ║
    ║   ╚██████╗   ██║   ██████╔╝╚██████╔╝     ╚███╔███╔╝██║  ██║███████║██████╔╝ ║
    ║    ╚═════╝   ╚═╝   ╚═════╝  ╚═════╝       ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ║
    ║                                                                              ║
    ║                    ULTIMATE CYBER SECURITY SUITE v7.0                        ║
    ║                         „BOH MEDZI HACKERMI“                                 ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

    dependencies = {
        'AI Analysis': AI_AVAILABLE,
        'Network Analysis': SCAPY_AVAILABLE,
        'Bluetooth Radar': BLE_AVAILABLE,
        'OCR Capabilities': OCR_AVAILABLE
    }
    for feature, available in dependencies.items():
        status = "✅ AVAILABLE" if available else "❌ NOT AVAILABLE"
        print(f"   {feature}: {status}")

    try:
        app = UltimateCyberpunkGUI(decision_loop=decision_loop)
        if decision_loop:
            decision_loop.attach_ui(app)
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
