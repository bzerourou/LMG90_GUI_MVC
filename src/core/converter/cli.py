"""Interface ligne de commande du convertisseur."""
import argparse
import json
import sys
from pathlib import Path

from .converter import Converter


def convert(script_path: Path, output_path: Path, verbose: bool = True) -> bool:
    if not script_path.exists():
        print(f"Fichier introuvable : {script_path}", file=sys.stderr)
        return False
    if verbose:
        print(f"Conversion de : {script_path}")
        print(f"Destination   : {output_path}")
    cv      = Converter(script_path)
    cv.run()
    project = cv.to_lmgc90_dict()
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    if verbose:
        _print_report(cv, project)
    return True



def _print_report(cv: Converter, project: dict) -> None:
    def _count_origin(avatars, origin):
        return sum(1 for a in avatars if a.get('__origin') == origin)

    avs  = project['avatars']
    n_m  = _count_origin(avs, 'manual')
    n_l  = _count_origin(avs, 'loop')
    n_ms = sum(1 for a in avs if a.get('type') == 'mesh')
    n_ea = sum(1 for a in avs if a.get('type') == 'emptyAvatar')
    n_ma = _count_origin(avs, 'masonry')

    print(f"\nResume :")
    print(f"  Dimension      : {project['dimension']}D")
    print(f"  Materiaux      : {len(project['materials'])}")
    print(f"  Modeles        : {len(project['models'])}")
    print(f"  Avatars        : {len(avs)}"
          f"  (manuel={n_m}, boucle={n_l}, maille={n_ms}, "
          f"emptyAvatar={n_ea}, maconnerie={n_ma})")
    print(f"  Lois contact   : {len(project['contact_laws'])}")
    print(f"  Visibilites    : {len(project['visibility_rules'])}")
    print(f"  Operations DOF : {len(project['operations'])}")
    print(f"  Granulo        : {len(project['granulo_generations'])}")
    print(f"  PostPro        : {len(project['postpro_creations'])}")
    print(f"  Maconnerie     : {len(project['masonry_patterns'])} pattern(s)")

    forl  = project['for_loops']
    if forl:
        print(f"\nBoucles ({len(forl)}) :")
        for i, fl in enumerate(forl):
            n = fl.get('generated_indices', [])
            print(f"  [{i}] for {fl['loop_var']} in "
                  f"range({fl['start_expr']},{fl['end_expr']}) "
                  f"— {len(n)} avatars")

    dv = project['dynamic_vars']
    if dv:
        print(f"\nVariables dynamiques ({len(dv)}) :")
        for k, v in list(dv.items())[:15]:
            print(f"  {k} = {v!r}")
        if len(dv) > 15:
            print(f"  ... ({len(dv)-15} de plus)")

    if cv._warnings:
        print(f"\nAvertissements ({len(cv._warnings)}) :")
        for w in cv._warnings[:10]:
            print(f"  • {w.split(chr(10))[0]}")

    print(f"\nFichier ecrit.")



def main():
    parser = argparse.ArgumentParser(
        description='Convertit un script pylmgc90 en projet .lmgc90 pour LMGC90_GUI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('script', type=Path, help='Fichier Python source (.py)')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='Fichier de sortie (.lmgc90).')
    parser.add_argument('--check', action='store_true',
                        help='Verifie sans ecrire le fichier.')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Sortie minimale.')

    args   = parser.parse_args()
    script = args.script.resolve()
    output = args.output or script.with_suffix('.lmgc90')

    if args.check:
        cv = Converter(script)
        cv.run()
        project = cv.to_lmgc90_dict()
        print(json.dumps(project, indent=2, ensure_ascii=False))
        return

    ok = convert(script, output, verbose=not args.quiet)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()