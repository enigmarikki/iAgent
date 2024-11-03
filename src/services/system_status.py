import psutil
from textual.widgets import Static, Label
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from datetime import datetime
import pytz
import asyncio

class SystemStatus(Static):
    """System status component showing system information"""
    
    # Define reactive variables directly
    connection = reactive("Active")
    latency = reactive("0ms")
    memory = reactive("0MB")
    
    DEFAULT_CSS = """
    SystemStatus {
        width: 100%;
        padding: 1;
        background: $surface-darken-1;
        border: solid $primary;
        margin: 1;
    }

    .status-header {
        text-style: bold;
        padding: 1;
    }

    .status-item {
        margin: 1 0;
        padding: 0 1;
    }

    .status-good {
        color: $success;
    }

    .status-error {
        color: $error;
    }
    """

    def __init__(self):
        super().__init__()
        self._start_time = datetime.now()
        self._update_task = None

    def compose(self) -> ComposeResult:
        """Create system status layout"""
        with Container():
            yield Label("System Status", classes="status-header")
            with Vertical():
                # Time display
                yield Static(id="time-display", classes="status-item")
                # Connection status
                yield Static(id="connection-display", classes="status-item")
                # Latency
                yield Static(id="latency-display", classes="status-item")
                # Memory usage
                yield Static(id="memory-display", classes="status-item")
                # Uptime
                yield Static(id="uptime-display", classes="status-item")

    def on_mount(self) -> None:
        """Start the update task when the widget is mounted"""
        self._update_task = asyncio.create_task(self._update_loop())
        self.update_displays()

    async def on_unmount(self) -> None:
        """Clean up the update task when the widget is unmounted"""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    def update_displays(self) -> None:
        """Update all display elements"""
        if not self.is_attached:
            return

        # Update time
        current_time = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        self.query_one("#time-display").update(f"Time (UTC): {current_time}")

        # Update connection status
        status_class = "status-good" if self.connection == "Active" else "status-error"
        self.query_one("#connection-display").update(
            f"Connection: [class={status_class}]{self.connection}[/]"
        )

        # Update latency
        self.query_one("#latency-display").update(f"Latency: {self.latency}")

        # Update memory
        self.query_one("#memory-display").update(f"Memory Usage: {self.memory}")

        # Update uptime
        uptime = datetime.now() - self._start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        seconds = int(uptime.total_seconds() % 60)
        self.query_one("#uptime-display").update(
            f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )

    async def _update_loop(self) -> None:
        """Periodically update system information"""
        while True:
            try:
                # Update memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                self.memory = f"{memory_info.rss / (1024 * 1024):.1f}MB"

                # Update latency (simulated with CPU usage)
                self.latency = f"{psutil.cpu_percent()}ms"

                # Update connection (simplified check)
                network_interfaces = psutil.net_if_stats()
                self.connection = "Active" if any(nic.isup for nic in network_interfaces.values()) else "Inactive"

                # Update all displays
                self.update_displays()

            except Exception as e:
                print(f"Error updating system status: {e}")

            await asyncio.sleep(1)

    def watch_connection(self, new_value: str) -> None:
        """Watch for connection status changes"""
        self.update_displays()

    def watch_latency(self, new_value: str) -> None:
        """Watch for latency changes"""
        self.update_displays()

    def watch_memory(self, new_value: str) -> None:
        """Watch for memory usage changes"""
        self.update_displays()
