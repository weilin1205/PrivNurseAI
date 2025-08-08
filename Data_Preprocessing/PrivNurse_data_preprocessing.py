import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
import re
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import psutil
import time
from tqdm.auto import tqdm
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rich console for beautiful output
console = Console()

# --- 配置類 ---
@dataclass
class Config:
    """程式配置"""
    BASE_DIR: Path = Path("病歷摘要資料")
    SUMMARY_DIR: Path = None
    CONSULT_DIR: Path = None
    LAB_DIR: Path = None
    NURSING_DIR: Path = None
    OUTPUT_FILE: str = "training_dataset_with_length_hint.xlsx"
    MAX_WORKERS: int = 4  # 並行處理的工作執行緒數
    
    def __post_init__(self):
        self.SUMMARY_DIR = self.BASE_DIR / "出院摘要"
        self.CONSULT_DIR = self.BASE_DIR / "會診紀錄"
        self.LAB_DIR = self.BASE_DIR / "檢驗報告"
        self.NURSING_DIR = self.BASE_DIR / "護理紀錄"

# --- 資料結構 ---
@dataclass
class Event:
    """時間事件資料結構"""
    timestamp: datetime
    xml_string: str

# --- 進度追蹤器 ---
class ProgressTracker:
    """進度追蹤器，提供詳細的進度資訊"""
    
    def __init__(self):
        self.start_time = time.time()
        self.stats = {
            'files_loaded': 0,
            'records_processed': 0,
            'errors': 0,
            'memory_usage': 0
        }
    
    def update_memory_usage(self):
        """更新記憶體使用情況"""
        process = psutil.Process(os.getpid())
        self.stats['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
    
    def get_elapsed_time(self):
        """獲取經過時間"""
        return time.time() - self.start_time
    
    def create_status_table(self):
        """創建狀態表格"""
        table = Table(title="處理狀態")
        table.add_column("項目", style="cyan", no_wrap=True)
        table.add_column("數值", style="magenta")
        
        table.add_row("載入檔案數", str(self.stats['files_loaded']))
        table.add_row("處理記錄數", str(self.stats['records_processed']))
        table.add_row("錯誤數", str(self.stats['errors']))
        table.add_row("記憶體使用", f"{self.stats['memory_usage']:.1f} MB")
        table.add_row("執行時間", f"{self.get_elapsed_time():.1f} 秒")
        
        return table

# --- 輔助函式 ---
class TextProcessor:
    """文字處理工具類"""
    
    @staticmethod
    def clean_text(text: Any) -> str:
        """清理文字中的HTML標籤並確保是字串格式"""
        if pd.isna(text):
            return ""
        text_str = str(text)
        return TextProcessor._html_pattern.sub('', text_str).strip()
    
    _html_pattern = re.compile(r'</?p>')

class DataLoader:
    """資料載入工具類"""
    
    def __init__(self, progress_tracker: ProgressTracker):
        self.progress_tracker = progress_tracker
    
    def load_excel_file(self, file_path: Path, pbar: Optional[tqdm] = None) -> Optional[pd.DataFrame]:
        """載入單個Excel檔案，帶錯誤處理和進度更新"""
        try:
            if file_path.exists():
                if pbar:
                    pbar.set_description(f"載入 {file_path.name}")
                df = pd.read_excel(file_path, engine='openpyxl')
                self.progress_tracker.stats['files_loaded'] += 1
                if pbar:
                    pbar.update(1)
                return df
            else:
                logger.warning(f"File not found: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            self.progress_tracker.stats['errors'] += 1
            if pbar:
                pbar.update(1)
            return None
    
    def load_and_concat_excel_parallel(self, directory: Path, file_prefix: str, 
                                     max_workers: int = 4) -> pd.DataFrame:
        """並行讀取指定目錄下所有part開頭的Excel檔案並合併"""
        all_files = [directory / f"{file_prefix}_part{i}.xlsx" for i in range(1, 5)]
        existing_files = [f for f in all_files if f.exists()]
        
        console.print(f"\n[bold blue]載入 {file_prefix} 資料[/bold blue]")
        console.print(f"找到 {len(existing_files)} 個檔案")
        
        if not existing_files:
            logger.warning(f"No files found for prefix: {file_prefix}")
            return pd.DataFrame()
        
        df_list = []
        
        # 創建進度條
        with tqdm(total=len(existing_files), 
                 desc=f"載入 {file_prefix}", 
                 unit="檔案",
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.load_excel_file, f, None): f 
                    for f in existing_files
                }
                
                for future in as_completed(future_to_file):
                    df = future.result()
                    if df is not None:
                        df_list.append(df)
                    pbar.update(1)
                    self.progress_tracker.update_memory_usage()
        
        if not df_list:
            return pd.DataFrame()
        
        # 合併資料
        console.print(f"[green]✓[/green] 合併 {len(df_list)} 個檔案...")
        result = pd.concat(df_list, ignore_index=True)
        console.print(f"[green]✓[/green] 載入完成，共 {len(result)} 筆記錄")
        
        return result

class LengthClassifier:
    """長度分類工具"""
    
    @staticmethod
    def get_length_hint(word_count: Any) -> str:
        """根據字數返回長度提示標籤"""
        if pd.isna(word_count):
            return "unknown"
        
        try:
            count = int(word_count)
            if count < 400:
                return "short"
            elif count < 700:
                return "medium"
            else:
                return "long"
        except (ValueError, TypeError):
            return "unknown"

class EventFormatter:
    """事件格式化工具類"""
    
    def __init__(self, progress_tracker: ProgressTracker):
        self.progress_tracker = progress_tracker
    
    def format_nursing_events(self, df_nursing: pd.DataFrame) -> List[Event]:
        """將護理紀錄DataFrame轉換為Event列表"""
        if df_nursing.empty:
            return []
        
        events = []
        
        # 批次處理時間格式化
        df_nursing = df_nursing.copy()
        df_nursing['時間'] = df_nursing['時間'].astype(str).str.zfill(4).str.replace(':', '')
        
        # 向量化操作建立時間戳
        df_nursing['timestamp_str'] = df_nursing['日期'].astype(str) + df_nursing['時間']
        df_nursing['timestamp'] = pd.to_datetime(df_nursing['timestamp_str'], 
                                                format='%Y%m%d%H%M', errors='coerce')
        
        # 過濾掉無效時間戳
        valid_rows = df_nursing.dropna(subset=['timestamp'])
        
        for _, row in valid_rows.iterrows():
            xml_parts = []
            
            # 建立生命徵象部分
            if pd.notna(row.get('類別')) and pd.notna(row.get('數值紀錄')):
                xml_parts.append(
                    f'<VitalSign type="{row["類別"]}" value="{TextProcessor.clean_text(row["數值紀錄"])}" />'
                )
            
            # 建立SOAP記錄部分
            soap_fields = [
                ('Subjective', 'RECORD_S'),
                ('Objective', 'RECORD_O'),
                ('Intervention', 'RECORD_I'),
                ('Evaluation', 'RECORD_E'),
                ('NarrativeNote', 'RECORD_N')
            ]
            
            soap_parts = []
            for tag, field in soap_fields:
                content = TextProcessor.clean_text(row.get(field, ''))
                if content:
                    soap_parts.append(f'<{tag}>{content}</{tag}>')
            
            if soap_parts:
                xml_parts.append(f'<SOAPNote>\n{"".join(soap_parts)}\n</SOAPNote>')
            
            # 組合XML
            if xml_parts:
                xml_string = f"""<NursingEvent timestamp="{row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}">
{chr(10).join(xml_parts)}
</NursingEvent>"""
                events.append(Event(row['timestamp'], xml_string))
        
        return events
    
    def format_lab_events(self, df_lab: pd.DataFrame) -> List[Event]:
        """將檢驗報告DataFrame轉換為Event列表"""
        if df_lab.empty:
            return []
        
        events = []
        df_lab = df_lab.copy()
        df_lab['檢驗日期'] = pd.to_datetime(df_lab['檢驗日期'], errors='coerce')
        
        # 過濾掉無效日期
        valid_df = df_lab.dropna(subset=['檢驗日期'])
        
        # 按日期分組
        for date, group in valid_df.groupby(valid_df['檢驗日期'].dt.date):
            timestamp = pd.to_datetime(date)
            
            # 使用列表推導式構建項目XML
            items_xml = '\n'.join([
                f'<Item name="{TextProcessor.clean_text(row["檢驗項目"])}">'
                f'{TextProcessor.clean_text(row["檢驗結果"])}</Item>'
                for _, row in group.iterrows()
            ])
            
            xml_string = f"""<LabReportGroup date="{date.strftime('%Y-%m-%d')}">
{items_xml}
</LabReportGroup>"""
            
            events.append(Event(timestamp, xml_string))
        
        return events
    
    def format_consult_events(self, df_consult: pd.DataFrame) -> List[Event]:
        """將會診紀錄DataFrame轉換為Event列表"""
        if df_consult.empty:
            return []
        
        events = []
        df_consult = df_consult.copy()
        df_consult['回覆時間'] = pd.to_datetime(df_consult['回覆時間'], errors='coerce')
        
        # 過濾掉無效時間戳
        valid_rows = df_consult.dropna(subset=['回覆時間'])
        
        for _, row in valid_rows.iterrows():
            content = TextProcessor.clean_text(row.get("回覆內容", ""))
            if content:
                xml_string = f"""<Consultation timestamp="{row['回覆時間'].strftime('%Y-%m-%d %H:%M:%S')}">
    <Content>
    {content}
    </Content>
</Consultation>"""
                events.append(Event(row['回覆時間'], xml_string))
        
        return events

class PatientDataProcessor:
    """病患資料處理器"""
    
    def __init__(self, config: Config, progress_tracker: ProgressTracker):
        self.config = config
        self.progress_tracker = progress_tracker
        self.text_processor = TextProcessor()
        self.length_classifier = LengthClassifier()
        self.event_formatter = EventFormatter(progress_tracker)
    
    def process_patient_record(self, summary_row: pd.Series, 
                             grouped_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """處理單個病患記錄"""
        patient_id = summary_row['序號']
        
        # 收集所有時間事件
        all_events = []
        
        # 處理各類記錄
        event_processors = [
            ('consults', self.event_formatter.format_consult_events),
            ('labs', self.event_formatter.format_lab_events),
            ('nursing', self.event_formatter.format_nursing_events)
        ]
        
        for data_key, formatter in event_processors:
            try:
                if grouped_data[data_key] and patient_id in grouped_data[data_key].groups:
                    patient_data = grouped_data[data_key].get_group(patient_id)
                    all_events.extend(formatter(patient_data))
            except Exception as e:
                logger.warning(f"Error processing {data_key} for patient {patient_id}: {e}")
                self.progress_tracker.stats['errors'] += 1
        
        # 按時間排序所有事件
        all_events.sort(key=lambda x: x.timestamp)
        
        # 提取排序後的XML字串
        sorted_events_xml = "\n".join([event.xml_string for event in all_events])
        
        # 根據字數決定長度提示標籤
        length_hint_tag = self.length_classifier.get_length_hint(summary_row.get('words'))
        
        # 建立輸入文本
        input_text = self._build_input_text(summary_row, sorted_events_xml, length_hint_tag)
        
        # 獲取目標輸出
        output_text = self.text_processor.clean_text(summary_row.get('治療經過'))
        
        # 更新統計
        self.progress_tracker.stats['records_processed'] += 1
        
        # 確保有輸出才返回
        if output_text:
            return {
                "input_text": input_text,
                "output_text": output_text
            }
        return None
    
    def _build_input_text(self, summary_row: pd.Series, events_xml: str, 
                         length_hint: str) -> str:
        """建立格式化的輸入文本"""
        fields = {
            'PrimaryDiagnosis': '主要診斷',
            'SecondaryDiagnosis': '次要診斷',
            'PastMedicalHistory': '過去病史',
            'ChiefComplaint': '主訴',
            'PresentIllness': '現在病史'
        }
        
        summary_parts = []
        for tag, field in fields.items():
            content = self.text_processor.clean_text(summary_row.get(field, ''))
            if content:
                summary_parts.append(f'<{tag}>{content}</{tag}>')
        
        return f"""<PatientEncounter summary_length_style="{length_hint}">
    <Summary>
        {chr(10).join(summary_parts)}
    </Summary>
    <ChronologicalEvents>
        {events_xml}
    </ChronologicalEvents>
</PatientEncounter>"""

def process_patients_batch(processor: PatientDataProcessor, 
                          summaries_batch: pd.DataFrame,
                          grouped_data: Dict[str, Any],
                          batch_num: int,
                          total_batches: int) -> List[Dict[str, str]]:
    """處理一批病患資料"""
    results = []
    
    # 創建批次進度條
    batch_desc = f"批次 {batch_num}/{total_batches}"
    for _, summary_row in tqdm(summaries_batch.iterrows(), 
                              total=len(summaries_batch),
                              desc=batch_desc,
                              unit="病患",
                              position=1,
                              leave=False,
                              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
        result = processor.process_patient_record(summary_row, grouped_data)
        if result:
            results.append(result)
    
    return results

def main():
    """主執行函式"""
    console.print(Panel.fit("[bold blue]病歷摘要訓練資料集生成器[/bold blue]", 
                           subtitle="v2.0 - 詳細進度版"))
    
    config = Config()
    progress_tracker = ProgressTracker()
    processor = PatientDataProcessor(config, progress_tracker)
    data_loader = DataLoader(progress_tracker)
    
    try:
        # ========== 步驟 1: 載入資料 ==========
        console.print("\n[bold yellow]步驟 1: 載入所有資料檔案[/bold yellow]")
        console.print("="*50)
        
        # 並行載入所有資料
        data = {}
        data_types = [
            ('summaries', config.SUMMARY_DIR, "急診出院摘要"),
            ('consults', config.CONSULT_DIR, "會診紀錄"),
            ('labs', config.LAB_DIR, "檢驗報告"),
            ('nursing', config.NURSING_DIR, "護理紀錄")
        ]
        
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]載入資料集...", total=len(data_types))
            
            for key, directory, prefix in data_types:
                data[key] = data_loader.load_and_concat_excel_parallel(
                    directory, prefix, config.MAX_WORKERS
                )
                progress.update(task, advance=1)
        
        load_time = time.time() - start_time
        
        # 顯示載入統計
        console.print("\n[bold green]✓ 資料載入完成![/bold green]")
        
        stats_table = Table(title="載入統計")
        stats_table.add_column("資料類型", style="cyan", no_wrap=True)
        stats_table.add_column("記錄數", style="magenta")
        stats_table.add_column("記憶體使用", style="yellow")
        
        for key, directory, prefix in data_types:
            if not data[key].empty:
                memory_usage = data[key].memory_usage(deep=True).sum() / 1024 / 1024
                stats_table.add_row(prefix, f"{len(data[key]):,}", f"{memory_usage:.1f} MB")
        
        stats_table.add_row("", "", "")
        stats_table.add_row("[bold]總計[/bold]", 
                           f"[bold]{sum(len(df) for df in data.values()):,}[/bold]", 
                           f"[bold]{progress_tracker.stats['memory_usage']:.1f} MB[/bold]")
        
        console.print(stats_table)
        console.print(f"\n載入時間: {load_time:.2f} 秒")
        
        # ========== 步驟 2: 資料分組 ==========
        console.print("\n[bold yellow]步驟 2: 按病患ID分組資料[/bold yellow]")
        console.print("="*50)
        
        grouped_data = {}
        
        with tqdm(total=3, desc="資料分組", unit="類型") as pbar:
            for key in ['consults', 'labs', 'nursing']:
                if not data[key].empty:
                    grouped_data[key] = data[key].groupby('序號')
                else:
                    grouped_data[key] = None
                pbar.update(1)
                pbar.set_postfix({f"{key}_groups": len(grouped_data[key].groups) if grouped_data[key] else 0})
        
        console.print("[green]✓[/green] 分組完成!")
        
        # ========== 步驟 3: 處理病患記錄 ==========
        console.print(f"\n[bold yellow]步驟 3: 處理 {len(data['summaries'])} 筆病患記錄[/bold yellow]")
        console.print("="*50)
        
        final_data = []
        batch_size = 100  # 每批處理的記錄數
        total_records = len(data['summaries'])
        total_batches = (total_records + batch_size - 1) // batch_size
        
        # 主進度條
        with tqdm(total=total_records, 
                 desc="總進度", 
                 unit="病患",
                 position=0,
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as main_pbar:
            
            # 批次處理
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, total_records)
                
                batch_data = data['summaries'].iloc[start_idx:end_idx]
                
                # 處理批次
                batch_results = process_patients_batch(
                    processor, batch_data, grouped_data, 
                    batch_num + 1, total_batches
                )
                
                final_data.extend(batch_results)
                main_pbar.update(len(batch_data))
                
                # 更新記憶體使用情況
                progress_tracker.update_memory_usage()
                main_pbar.set_postfix({
                    '有效記錄': len(final_data),
                    '記憶體': f"{progress_tracker.stats['memory_usage']:.1f}MB",
                    '錯誤': progress_tracker.stats['errors']
                })
        
        # ========== 步驟 4: 儲存結果 ==========
        console.print(f"\n[bold yellow]步驟 4: 儲存最終資料集[/bold yellow]")
        console.print("="*50)
        
        df_final = pd.DataFrame(final_data)
        
        # 儲存前的統計
        console.print("\n[cyan]資料集統計:[/cyan]")
        
        # 計算統計資訊
        input_lengths = df_final['input_text'].str.len()
        output_lengths = df_final['output_text'].str.len()
        
        stats_dict = {
            "總記錄數": len(df_final),
            "平均輸入長度": f"{input_lengths.mean():.0f} 字元",
            "平均輸出長度": f"{output_lengths.mean():.0f} 字元",
            "最長輸入": f"{input_lengths.max():,} 字元",
            "最短輸入": f"{input_lengths.min():,} 字元",
            "最長輸出": f"{output_lengths.max():,} 字元",
            "最短輸出": f"{output_lengths.min():,} 字元",
        }
        
        for key, value in stats_dict.items():
            console.print(f"  {key}: [yellow]{value}[/yellow]")
        
        # 儲存檔案
        with tqdm(total=1, desc="儲存Excel檔案", unit="檔案") as pbar:
            with pd.ExcelWriter(config.OUTPUT_FILE, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False)
            pbar.update(1)
        
        # ========== 完成 ==========
        total_time = progress_tracker.get_elapsed_time()
        
        console.print("\n" + "="*50)
        console.print(Panel.fit(
            f"[bold green]✓ 成功生成 {config.OUTPUT_FILE}[/bold green]\n"
            f"[yellow]總共處理 {len(df_final)} 筆記錄[/yellow]\n"
            f"[cyan]總執行時間: {total_time:.2f} 秒[/cyan]",
            title="[bold]完成[/bold]"
        ))
        
        # 最終統計表
        final_table = progress_tracker.create_status_table()
        console.print("\n", final_table)
        
    except Exception as e:
        console.print(f"\n[bold red]✗ 發生錯誤:[/bold red] {str(e)}")
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise
    finally:
        # 清理資源
        console.print("\n[dim]清理資源...[/dim]")

if __name__ == "__main__":
    # 安裝必要套件提示
    try:
        import rich
    except ImportError:
        print("請先安裝 rich 套件: pip install rich")
        exit(1)
    
    try:
        import psutil
    except ImportError:
        print("請先安裝 psutil 套件: pip install psutil")
        exit(1)
    
    main()