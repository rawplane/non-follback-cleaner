import os
import sys
import time
import re
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import box

import config
import storage
from unfollower import InstagramUnfollower

app = typer.Typer(help="Auto Unfollow Instagram (Non-Follback Cleaner) - Playwright Edition")
console = Console()


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]AUTO UNFOLLOW INSTAGRAM (NON-FOLLBACK CLEANER)[/bold cyan]\n"
            "[dim]Playwright + SQLite Engine • Brave Browser Edition[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


def save_results_to_file(non_followers: list, my_username: str) -> str:
    filename = f"non_followers_{my_username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Non-Follback Account List for @{my_username}\n")
            f.write(f"# Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(non_followers)} accounts\n\n")
            for u in non_followers:
                f.write(f"{u}\n")
        return filename
    except Exception as e:
        console.print(f"[yellow][!] Gagal simpan file txt: {e}[/yellow]")
        return ""


@app.command("scan")
def scan_cmd():
    """Scan akun yang tidak follow back."""
    unfollower = InstagramUnfollower(dry_run=True)
    try:
        with console.status("[cyan]Membuka Brave Browser...[/cyan]", spinner="dots"):
            unfollower.init_browser()

        if not unfollower.check_login(lambda msg: console.print(f"[dim]{msg}[/dim]")):
            console.print("[red][✗] Batal: Sesi Instagram belum login.[/red]")
            return

        my_user = unfollower.get_my_username()
        console.print(f"[bold green][*] Akun aktif: @{my_user}[/bold green]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task_following = progress.add_task("[cyan]Scanning Following...", total=100)
            task_followers = progress.add_task("[green]Scanning Followers...", total=100)

            def update_progress(kind: str, cur: int, total: int):
                tot = max(total, 1)
                pct = min(100.0, (cur / tot) * 100.0)
                if kind == "following":
                    progress.update(task_following, completed=pct, description=f"[cyan]Following ({cur}/{tot})")
                else:
                    progress.update(task_followers, completed=pct, description=f"[green]Followers ({cur}/{tot})")

            following, followers, non_followers = unfollower.scan_non_followers(progress_callback=update_progress)

        table = Table(title="Statistik Scan Akun", box=box.SIMPLE_HEAVY)
        table.add_column("Metrik", style="bold")
        table.add_column("Jumlah", justify="right")

        table.add_row("Total Following (Diikuti)", f"[cyan]{len(following)}[/cyan]")
        table.add_row("Total Followers (Pengikut)", f"[green]{len(followers)}[/green]")
        table.add_row("Tidak Follow Back (Non-Follback)", f"[bold red]{len(non_followers)}[/bold red]")
        console.print(table)

        if not non_followers:
            console.print("\n[bold green][✓] Semua akun sudah saling follow atau terlindungi Whitelist.[/bold green]\n")
            return

        txt_file = save_results_to_file(non_followers, my_user)
        if txt_file:
            console.print(f"[green][✓] Daftar non-follback tersimpan di: [bold]{txt_file}[/bold][/green]")

        disp_table = Table(title=f"Daftar Non-Follback (Preview {min(30, len(non_followers))} dari {len(non_followers)})", box=box.ROUNDED)
        disp_table.add_column("No", justify="right", style="dim", width=5)
        disp_table.add_column("Username", style="yellow")

        for idx, u in enumerate(non_followers[:30], 1):
            disp_table.add_row(str(idx), f"@{u}")
        console.print(disp_table)

        if len(non_followers) > 30:
            console.print(f"[dim]... dan {len(non_followers) - 30} akun lainnya (cek database atau file txt).[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow][!] Proses dibatalkan user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red][✗] Terjadi error: {e}[/red]")
    finally:
        unfollower.close()


@app.command("unfollow")
def unfollow_cmd(
    dry_run: bool = typer.Option(True, "--dry-run/--real", help="Mode simulasi (dry-run) atau eksekusi nyata (real)."),
    batch_size: int = typer.Option(config.MAX_UNFOLLOW_LIMIT, "--batch-size", "-b", help="Batas unfollow per batch."),
):
    """Jalankan proses auto unfollow secara batch."""
    unfollower = InstagramUnfollower(dry_run=dry_run)
    try:
        with console.status("[cyan]Membuka Brave Browser...[/cyan]", spinner="dots"):
            unfollower.init_browser()

        if not unfollower.check_login(lambda msg: console.print(f"[dim]{msg}[/dim]")):
            console.print("[red][✗] Batal: Sesi Instagram belum login.[/red]")
            return

        my_user = unfollower.get_my_username()
        console.print(f"[bold green][*] Akun aktif: @{my_user}[/bold green]")

        # Ambil daftar target dari scan sebelumnya atau lakukan scan baru
        targets = storage.get_last_scan(my_user)
        if not targets:
            console.print("[yellow][*] Belum ada data scan lokal. Melakukan scan akun...[/yellow]")
            _, _, targets = unfollower.scan_non_followers()

        # Filter dengan whitelist terbaru
        active_whitelist = config.load_whitelist()
        targets = [u for u in targets if u.lower() not in active_whitelist]

        if not targets:
            console.print("[bold green][✓] Antrean non-follback kosong atau semua masuk whitelist.[/bold green]")
            return

        mode_str = "[yellow]SIMULASI (DRY-RUN)[/yellow]" if dry_run else "[bold red]REAL EXECUTION[/bold red]"
        console.print(Panel(
            f"Mode: {mode_str}\n"
            f"Total target non-follback: [bold cyan]{len(targets)}[/bold cyan] akun\n"
            f"Ukuran batch: [bold]{batch_size}[/bold] akun per sesi",
            title="Konfigurasi Eksekusi",
            border_style="yellow" if dry_run else "red",
        ))

        if not dry_run:
            confirm = Confirm.ask("[bold red]Yakin ingin melakukan unfollow nyata sekarang?[/bold red]", default=False)
            if not confirm:
                console.print("[yellow][!] Operasi dibatalkan.[/yellow]")
                return

        remaining_targets = list(targets)
        total_success = 0
        total_failed = 0
        batch_number = 1
        action_blocked = False

        while remaining_targets and not action_blocked:
            current_batch = remaining_targets[:batch_size]
            console.print(f"\n[bold cyan]=== BATCH #{batch_number}: {len(current_batch)} akun (Sisa antrean: {len(remaining_targets)}) ===[/bold cyan]")

            for idx, target in enumerate(current_batch, 1):
                global_idx = total_success + total_failed + 1
                console.print(f"[{idx}/{len(current_batch)}] (#{global_idx}) Target: [bold yellow]@{target}[/bold yellow]...", end=" ")

                success, msg = unfollower.unfollow_user(target)
                if success:
                    total_success += 1
                    console.print(f"[green][✓] {msg}[/green]")
                else:
                    total_failed += 1
                    console.print(f"[red][!] {msg}[/red]")
                    if "[WARNING]" in msg or "Action Block" in msg or "429" in msg:
                        action_blocked = True
                        console.print("\n[bold red][!] PERINGATAN KEAMANAN: Instagram mendeteksi pembatasan aksi (Action Block / Rate Limit)![/bold red]")
                        console.print("[yellow]Otomasi dihentikan seketika untuk keamanan akun Anda.[/yellow]\n")
                        break

            remaining_targets = remaining_targets[len(current_batch):]

            if action_blocked or not remaining_targets:
                break

            console.print(f"\n[dim]Ringkasan Batch #{batch_number}: {total_success} berhasil, {len(remaining_targets)} tersisa.[/dim]")
            next_count = min(batch_size, len(remaining_targets))

            console.print(f"\n[bold]Lanjut ke Batch #{batch_number + 1} ({next_count} akun berikutnya)?[/bold]")
            console.print(" [green][Y / Enter][/green] Lanjut langsung")
            console.print(" [yellow][J <detik>][/yellow]  Istirahat dahulu (misal: 'J 30')")
            console.print(" [red][N][/red]          Berhenti / Kembali ke menu")

            choice = Prompt.ask("Pilihan", default="Y").strip().lower()

            if choice in ["", "y", "ya", "yes", "lanjut"]:
                batch_number += 1
                continue
            elif choice.startswith("j"):
                match = re.search(r"\d+", choice)
                delay_sec = int(match.group()) if match else 30
                console.print(f"[yellow][*] Jeda istirahat selama {delay_sec} detik...[/yellow]")
                try:
                    for s in range(delay_sec, 0, -1):
                        console.print(f"    Lanjut dalam {s}s...", end="\r")
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow][!] Jeda dilewati.[/yellow]")
                batch_number += 1
                continue
            else:
                console.print("[yellow][*] Dihentikan oleh pengguna.[/yellow]")
                break

        # Simpan sisa target ke database
        storage.save_scan_results(my_user, remaining_targets)

        summary_table = Table(title="Laporan Eksekusi", box=box.ROUNDED)
        summary_table.add_column("Keterangan", style="bold")
        summary_table.add_column("Nilai", justify="right")
        summary_table.add_row("Total Batch", str(batch_number))
        summary_table.add_row("Berhasil Di-unfollow", f"[green]{total_success}[/green]")
        summary_table.add_row("Gagal / Dilewati", f"[yellow]{total_failed}[/yellow]")
        summary_table.add_row("Sisa Antrean", f"[cyan]{len(remaining_targets)}[/cyan]")
        summary_table.add_row("Status", "[red]Action Block[/red]" if action_blocked else "[green]Selesai Normal[/green]")
        console.print(summary_table)

    except KeyboardInterrupt:
        console.print("\n[yellow][!] Operasi dibatalkan user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red][✗] Error: {e}[/red]")
    finally:
        unfollower.close()


@app.command("whitelist")
def whitelist_cmd(
    action: str = typer.Argument("list", help="Aksi: list, add, remove"),
    username: Optional[str] = typer.Argument(None, help="Username target"),
):
    """Kelola akun yang terlindungi (Whitelist)."""
    act = action.lower()
    if act == "list":
        wl = storage.get_whitelist()
        table = Table(title=f"Daftar Akun Terlindungi (Whitelist) - Total {len(wl)}", box=box.ROUNDED)
        table.add_column("No", justify="right", width=5, style="dim")
        table.add_column("Username", style="cyan")

        if not wl:
            console.print("[yellow]Whitelist masih kosong.[/yellow]")
        else:
            for idx, u in enumerate(sorted(wl), 1):
                table.add_row(str(idx), f"@{u}")
            console.print(table)

    elif act == "add":
        if not username:
            username = Prompt.ask("Masukkan username yang ingin dilindungi")
        if storage.add_whitelist(username):
            console.print(f"[green][✓] Akun @{username.lstrip('@')} berhasil ditambahkan ke whitelist.[/green]")
        else:
            console.print("[red][✗] Username tidak valid.[/red]")

    elif act == "remove" or act == "del":
        if not username:
            username = Prompt.ask("Masukkan username yang ingin dihapus")
        if storage.remove_whitelist(username):
            console.print(f"[green][✓] Akun @{username.lstrip('@')} dihapus dari whitelist.[/green]")
        else:
            console.print(f"[yellow][!] Akun @{username.lstrip('@')} tidak ditemukan di whitelist.[/yellow]")
    else:
        console.print(f"[red]Aksi '{action}' tidak dikenal. Gunakan: list, add, atau remove.[/red]")


@app.command("logs")
def logs_cmd(limit: int = typer.Option(15, "--limit", "-n", help="Jumlah log riwayat terakhir")):
    """Lihat log aktivitas eksekusi cleaner."""
    logs = storage.get_recent_logs(limit=limit)
    if not logs:
        console.print("[yellow]Belum ada riwayat aktivitas di database.[/yellow]")
        return

    table = Table(title=f"Riwayat Aktivitas Terakhir (Limit {limit})", box=box.ROUNDED)
    table.add_column("Waktu", style="dim")
    table.add_column("Target", style="yellow")
    table.add_column("Aksi", style="cyan")
    table.add_column("Status")
    table.add_column("Pesan", style="dim")

    for row in logs:
        status_style = "green" if row["status"] == "success" else ("yellow" if row["status"] in ["dry_run", "skipped"] else "red")
        table.add_row(
            str(row["performed_at"]),
            f"@{row['target_username']}",
            str(row["action"]),
            f"[{status_style}]{row['status']}[/{status_style}]",
            str(row["message"] or "-"),
        )
    console.print(table)


@app.command("config")
def config_cmd():
    """Tampilkan info konfigurasi sistem."""
    table = Table(title="Konfigurasi Sistem & Environment", box=box.ROUNDED)
    table.add_column("Parameter", style="bold cyan")
    table.add_column("Nilai")

    table.add_row("Brave Binary", config.BRAVE_BINARY_PATH or "[red]Not Found[/red]")
    table.add_row("Automation Profile", config.AUTOMATION_PROFILE_DIR)
    table.add_row("Display Mode", "Headless (Background)" if config.HEADLESS_MODE else "GUI (Window Terbuka)")
    table.add_row("Batch Limit", f"{config.MAX_UNFOLLOW_LIMIT} akun")
    table.add_row("Safety Delay", f"{config.MIN_DELAY_SECONDS}s - {config.MAX_DELAY_SECONDS}s")
    table.add_row("Database SQLite", storage.DB_PATH)
    table.add_row("Whitelist File", config.WHITELIST_FILE)

    console.print(table)


def interactive_menu():
    """Tampilan menu interaktif CLI."""
    while True:
        print_banner()
        console.print("[bold]MENU UTAMA:[/bold]")
        console.print(" [green][1][/green] 🔍 Scan Akun Non-Follback (Analisis)")
        console.print(" [yellow][2][/yellow] 🧪 Jalankan Unfollow ([bold]SIMULASI / Dry-Run[/bold])")
        console.print(" [red][3][/red] 🚀 Jalankan Unfollow ([bold]REAL MODE[/bold])")
        console.print(" [cyan][4][/cyan] 📋 Kelola Whitelist (Akun Terlindungi)")
        console.print(" [blue][5][/blue] 📜 Riwayat Audit / Logs Database")
        console.print(" [magenta][6][/magenta] ⚙️  Info Konfigurasi Sistem")
        console.print(" [dim][0][/dim] 🚪 Keluar\n")

        choice = Prompt.ask("Pilih menu [0-6]", default="1").strip()

        if choice == "1":
            scan_cmd()
        elif choice == "2":
            unfollow_cmd(dry_run=True, batch_size=config.MAX_UNFOLLOW_LIMIT)
        elif choice == "3":
            unfollow_cmd(dry_run=False, batch_size=config.MAX_UNFOLLOW_LIMIT)
        elif choice == "4":
            console.print("\n[cyan]Sub-menu Whitelist:[/cyan]")
            console.print(" [1] Lihat Whitelist  [2] Tambah Akun  [3] Hapus Akun")
            sub = Prompt.ask("Pilih", default="1").strip()
            if sub == "1":
                whitelist_cmd(action="list", username=None)
            elif sub == "2":
                u = Prompt.ask("Masukkan username yang ingin dilindungi")
                whitelist_cmd(action="add", username=u)
            elif sub == "3":
                u = Prompt.ask("Masukkan username yang ingin dihapus")
                whitelist_cmd(action="remove", username=u)
        elif choice == "5":
            logs_cmd(limit=20)
        elif choice == "6":
            config_cmd()
        elif choice == "0":
            console.print("\n[green]Terima kasih! Selesai.[/green]\n")
            sys.exit(0)
        else:
            console.print("[red]Pilihan tidak valid.[/red]")

        Prompt.ask("\n[dim]Tekan Enter untuk kembali ke menu...[/dim]", default="")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Instagram Non-Follback Cleaner: jalankan tanpa argumen untuk interactive menu."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


if __name__ == "__main__":
    app()
