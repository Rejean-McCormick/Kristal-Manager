#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import random
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client


def log(message: str) -> None:
    print(message, flush=True)


def word_rgb(r: int, g: int, b: int) -> int:
    """
    Format couleur attendu par Word/VBA.
    """
    return r | (g << 8) | (b << 16)


def build_safe_rainbow_palette():
    """
    Palette arc-en-ciel lisible sur fond blanc.
    Pas de quasi-noir, orange garanti, pas de jaune trop pâle.

    Note:
    - un "jaune pur" ou "orange clair" est peu lisible sur fond blanc.
    - on utilise donc des variantes plus foncées: ambre, orange brûlé, etc.
    """
    rgb_colors = [
        (190, 0, 0),     # rouge foncé
        (210, 45, 0),    # rouge-orangé
        (215, 95, 0),    # orange
        (185, 120, 0),   # ambre / jaune foncé
        (125, 145, 0),   # vert-jaune sombre
        (0, 145, 55),    # vert
        (0, 140, 115),   # turquoise
        (0, 115, 190),   # bleu
        (65, 80, 200),   # indigo
        (120, 65, 190),  # violet
        (170, 45, 170),  # magenta
        (190, 0, 110),   # rose foncé
    ]
    return [word_rgb(r, g, b) for r, g, b in rgb_colors]


def iter_story_ranges(doc):
    """
    Parcourt les différentes zones Word :
    texte principal, en-têtes, pieds de page, notes, zones de texte, etc.
    """
    seen = set()
    index = 0

    for story in doc.StoryRanges:
        current = story
        while current is not None:
            key = (int(current.StoryType), int(current.Start), int(current.End))
            if key not in seen:
                seen.add(key)
                index += 1
                yield index, current
            current = current.NextStoryRange


def should_color(text: str, include_spaces: bool = False) -> bool:
    if not text:
        return False

    # Contrôles Word fréquents
    if text in ("\r", "\x07"):
        return False

    if include_spaces:
        return True

    return not text.isspace()


def estimate_total_characters(stories):
    total = 0
    for _, story in stories:
        try:
            total += int(story.Characters.Count)
        except Exception:
            pass
    return total


def colorize_story(
    story,
    palette,
    rng,
    include_spaces: bool,
    progress_every: int,
    global_state: dict,
    story_index: int,
):
    count = int(story.Characters.Count)
    changed = 0
    palette_len = len(palette)

    log(f"[zone {story_index}] {count} caractères détectés")

    start_story = time.perf_counter()

    for i in range(1, count + 1):  # Word = indexation 1-based
        ch = story.Characters(i)
        text = ch.Text

        global_state["processed"] += 1

        if should_color(text, include_spaces=include_spaces):
            ch.Font.Color = palette[rng.randrange(palette_len)]
            changed += 1
            global_state["colored"] += 1

        if progress_every > 0 and global_state["processed"] % progress_every == 0:
            elapsed = time.perf_counter() - global_state["start_time"]
            processed = global_state["processed"]
            total = global_state["total_chars"]

            rate = processed / elapsed if elapsed > 0 else 0.0
            if total > 0:
                percent = (processed / total) * 100
                remaining = max(total - processed, 0)
                eta = remaining / rate if rate > 0 else 0.0
                log(
                    f"[progression] {processed}/{total} "
                    f"({percent:.1f} %) | colorés={global_state['colored']} "
                    f"| {rate:.0f} car/s | ETA ~ {eta:.0f} s"
                )
            else:
                log(
                    f"[progression] {processed} caractères traités "
                    f"| colorés={global_state['colored']} "
                    f"| {rate:.0f} car/s"
                )

    elapsed_story = time.perf_counter() - start_story
    log(
        f"[zone {story_index}] terminé | colorés={changed} "
        f"| durée={elapsed_story:.1f} s"
    )

    return changed


def pick_output_path(src: Path, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    return src.with_name(f"{src.stem}_rainbow{src.suffix}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Applique une couleur rainbow aléatoire lisible à chaque lettre "
            "d'un document Word (.doc/.docx), avec logs de progression."
        )
    )
    parser.add_argument("input_file", help="Chemin du fichier .doc ou .docx")
    parser.add_argument(
        "-o", "--output",
        help="Chemin du fichier de sortie. Défaut : <nom>_rainbow<extension>"
    )
    parser.add_argument(
        "--include-spaces",
        action="store_true",
        help="Colorer aussi les espaces"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed aléatoire pour résultat reproductible"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Afficher Word pendant l'exécution"
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Afficher une ligne de progression tous les N caractères. Défaut : 1000"
    )

    args = parser.parse_args()

    src = Path(args.input_file).expanduser().resolve()
    if not src.exists():
        print(f"Erreur : fichier introuvable : {src}", file=sys.stderr)
        sys.exit(1)

    if src.suffix.lower() not in {".doc", ".docx"}:
        print("Erreur : le fichier doit être en .doc ou .docx", file=sys.stderr)
        sys.exit(1)

    dst = pick_output_path(src, args.output)

    if dst == src:
        print("Erreur : le fichier de sortie doit être différent du fichier source.", file=sys.stderr)
        sys.exit(1)

    palette = build_safe_rainbow_palette()
    rng = random.Random(args.seed)

    log(f"[1/6] Palette prête : {len(palette)} couleurs")
    log("[2/6] Initialisation de Word...")

    pythoncom.CoInitialize()
    word = None
    doc = None

    try:
        word = win32com.client.gencache.EnsureDispatch("Word.Application")
        word.Visible = bool(args.visible)
        word.DisplayAlerts = 0

        try:
            word.ScreenUpdating = False
        except Exception:
            pass

        log("[3/6] Ouverture du document...")
        doc = word.Documents.Open(str(src), ReadOnly=False)

        log("[4/6] Inventaire des zones à traiter...")
        stories = list(iter_story_ranges(doc))
        total_stories = len(stories)
        total_chars = estimate_total_characters(stories)

        log(f"Zones détectées : {total_stories}")
        log(f"Total estimé de caractères : {total_chars}")

        global_state = {
            "processed": 0,
            "colored": 0,
            "total_chars": total_chars,
            "start_time": time.perf_counter(),
        }

        log("[5/6] Coloration en cours...")
        total_changed = 0

        for story_index, story in stories:
            total_changed += colorize_story(
                story=story,
                palette=palette,
                rng=rng,
                include_spaces=args.include_spaces,
                progress_every=args.progress_every,
                global_state=global_state,
                story_index=story_index,
            )

        log("[6/6] Enregistrement du fichier...")
        if dst.exists():
            dst.unlink()

        doc.SaveAs2(str(dst))

        total_elapsed = time.perf_counter() - global_state["start_time"]
        rate = global_state["processed"] / total_elapsed if total_elapsed > 0 else 0.0

        log("Terminé")
        log(f"Fichier créé : {dst}")
        log(f"Caractères traités : {global_state['processed']}")
        log(f"Caractères colorés : {total_changed}")
        log(f"Vitesse moyenne : {rate:.0f} car/s")
        log(f"Durée totale : {total_elapsed:.1f} s")

    except Exception as e:
        print(f"Erreur Word/COM : {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass

        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass

        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()