"""Analyse statique du script source (variables, boucles for) via le module ast."""
import ast
from typing import Any, Dict, List, Optional, Tuple


class _AstAnalyzer:
    AVATAR_FUNCS: frozenset = frozenset({
        # Rigides 2D
        'rigidDisk', 'rigidJonc', 'rigidPolygon', 'rigidOvoidPolygon',
        'rigidDiscreteDisk', 'rigidCluster',
        'roughWall', 'fineWall', 'smoothWall', 'granuloRoughWall',
        # Rigides 3D
        'rigidSphere', 'rigidPlan', 'rigidCylinder', 'rigidPolyhedron',
        'roughWall3D', 'granuloRoughWall3D',
        # Maillages / deformables
        'buildMesh2D', 'buildMeshH8', 'buildMeshT3', 'buildMeshQ4',
        'buildMeshT6', 'buildMeshQ8',
        'readMesh', 'readMeshGMSH', 'readMeshVTK',
        'buildMeshedAvatar',
        'surfacicMeshToRigid3D', 'volumicMeshToRigid3D',
        # Avatar vide
        'avatar',
    })

    MASONRY_FUNCS: frozenset = frozenset({'buildRigidWall',
                                          'buildRigidWallWithoutHalfBricks'})

    STD_CONTAINERS: frozenset = frozenset({
        'bodies', 'avatars', 'avs', 'body_list', 'mats', 'mods',
        'tacts', 'svs', 'sees', 'post', 'posts',
    })

    def __init__(self, source: str):
        self._source = source
        self._tree:  Optional[ast.Module] = None
        self.dynamic_vars: Dict[str, Any] = {}
        self.for_loops:    List[dict]     = []
        self.warnings:     List[str]      = []

    def analyze(self) -> None:
        try:
            self._tree = ast.parse(self._source)
        except SyntaxError as exc:
            self.warnings.append(f"Erreur de syntaxe AST : {exc}")
            return
        self._extract_dynamic_vars()
        self._detect_for_loops()

    def _extract_dynamic_vars(self) -> None:
        env: Dict[str, Any] = {}
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    val = self._safe_eval(node.value, env)
                    if val is not None:
                        env[target.id] = val
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    val = self._safe_eval(node.value, env)
                    if val is not None:
                        env[node.target.id] = val
        self.dynamic_vars = {
            k: v for k, v in env.items()
            if isinstance(v, (int, float, str, bool)) and not k.startswith('_')
        }

    def _safe_eval(self, node, env: Dict[str, Any]) -> Any:
        try:
            val = ast.literal_eval(node)
            if isinstance(val, (int, float, str, bool)):
                return val
        except (ValueError, TypeError):
            pass
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                v = self._safe_eval(node.operand, env)
                return -v if isinstance(v, (int, float)) else None
            if isinstance(node.op, ast.UAdd):
                return self._safe_eval(node.operand, env)
        if isinstance(node, ast.BinOp):
            left  = self._safe_eval(node.left,  env)
            right = self._safe_eval(node.right, env)
            if left is not None and right is not None:
                try:
                    op = node.op
                    if isinstance(op, ast.Add):       return left + right
                    if isinstance(op, ast.Sub):       return left - right
                    if isinstance(op, ast.Mult):      return left * right
                    if isinstance(op, ast.Div):       return left / right
                    if isinstance(op, ast.FloorDiv):  return int(left // right)
                    if isinstance(op, ast.Mod):       return left % right
                    if isinstance(op, ast.Pow):       return left ** right
                except (ZeroDivisionError, OverflowError, TypeError):
                    pass
        return None

    def _detect_for_loops(self) -> None:
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, ast.For):
                desc = self._analyze_for(node, depth=0)
                if desc is not None:
                    self.for_loops.append(desc)

    def _analyze_for(self, node: ast.For, depth: int) -> Optional[dict]:
        if not isinstance(node.target, ast.Name):
            return None
        loop_var = node.target.id
        range_info    = self._parse_range(node.iter)
        linspace_info = self._parse_linspace(node.iter) if range_info is None else None
        if range_info is None and linspace_info is None:
            return None
        avatar_calls  = list(self._iter_avatar_calls(node.body))
        masonry_calls = list(self._iter_masonry_calls(node.body))
        if not avatar_calls and not masonry_calls:
            return None
        if linspace_info is not None:
            a_expr, b_expr, n_expr = linspace_info
            count    = self._resolve_int(n_expr)
            all_calls = avatar_calls or masonry_calls
            template  = self._build_template(all_calls[0], loop_var)
            return {
                'loop_var': loop_var, 'start_expr': a_expr, 'end_expr': b_expr,
                'step_expr': 'linspace', 'count': count, 'loop_type': 'Générique',
                'geometry': {'linspace': True, 'n_expr': n_expr,
                             'a_expr': a_expr, 'b_expr': b_expr},
                'template_config': template,
                'group_name': self._detect_group(node.body),
            }
        start_expr, end_expr, step_expr = range_info
        inner_for_nodes = [
            n for n in ast.walk(ast.Module(body=node.body, type_ignores=[]))
            if isinstance(n, ast.For) and n is not node
        ]
        inner_desc: Optional[dict] = None
        if inner_for_nodes and depth == 0:
            inner_desc = self._analyze_for(inner_for_nodes[0], depth=1)
        all_calls  = avatar_calls or masonry_calls
        loop_type, geometry = self._classify_geometry(
            loop_var, node.body, all_calls, range_info, inner_desc)
        template   = self._build_template(all_calls[0], loop_var)
        group_name = self._detect_group(node.body)
        count      = self._resolve_int(end_expr)
        return {
            'loop_var': loop_var, 'start_expr': start_expr,
            'end_expr': end_expr, 'step_expr': step_expr,
            'count': count, 'loop_type': loop_type,
            'geometry': geometry, 'template_config': template,
            'group_name': group_name,
        }

    def _parse_range(self, node) -> Optional[Tuple[str, str, str]]:
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == 'range'):
            return None
        args = node.args
        if len(args) == 1: return ('0', self._unparse(args[0]), '1')
        if len(args) == 2: return (self._unparse(args[0]), self._unparse(args[1]), '1')
        if len(args) == 3: return (self._unparse(args[0]), self._unparse(args[1]),
                                   self._unparse(args[2]))
        return None

    def _parse_linspace(self, node) -> Optional[Tuple[str, str, str]]:
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == 'linspace'
                and isinstance(func.value, ast.Name)
                and func.value.id in ('np', 'numpy')):
            return None
        args = node.args
        kws  = {kw.arg: kw.value for kw in node.keywords}
        if len(args) >= 2:
            a_expr = self._unparse(args[0])
            b_expr = self._unparse(args[1])
            n_node = args[2] if len(args) >= 3 else kws.get('num')
            n_expr = self._unparse(n_node) if n_node is not None else '50'
            return (a_expr, b_expr, n_expr)
        if 'start' in kws and 'stop' in kws:
            n_node = kws.get('num')
            n_expr = self._unparse(n_node) if n_node is not None else '50'
            return (self._unparse(kws['start']), self._unparse(kws['stop']), n_expr)
        return None

    def _iter_avatar_calls(self, body: list):
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.AVATAR_FUNCS):
                yield node

    def _iter_masonry_calls(self, body: list):
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.MASONRY_FUNCS):
                yield node

    def _loop_dependent_vars(self, body: list, loop_var: str) -> frozenset:
        depends: set = {loop_var}
        changed = True
        module_stub = ast.Module(body=body, type_ignores=[])
        while changed:
            changed = False
            for node in ast.iter_child_nodes(module_stub):
                if not isinstance(node, ast.Assign):
                    continue
                rhs = self._unparse(node.value)
                if not any(dep in rhs for dep in depends):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in depends:
                        depends.add(target.id)
                        changed = True
        return frozenset(depends)

    def _classify_geometry(self, loop_var, body, avatar_calls,
                           range_info, inner_desc) -> Tuple[str, dict]:
        if inner_desc is not None and inner_desc.get('loop_type') in ('Ligne', 'Grille', 'Générique'):
            inner_geom = inner_desc.get('geometry', {})
            return ('Grille', {
                'nx_expr': range_info[1], 'ny_expr': inner_desc['end_expr'],
                'dx_expr': self._extract_step_in_body(loop_var, body, axis=0),
                'dy_expr': inner_geom.get('dy_expr', ''),
                'inner_loop_var': inner_desc['loop_var'],
            })
        cx_src, cy_src = None, None
        for call in avatar_calls:
            ce = self._extract_center_exprs(call)
            if ce is not None:
                cx_src, cy_src = ce
                break
        if cx_src is None:
            return ('Générique', {})
        dep_vars = self._loop_dependent_vars(body, loop_var)
        trig_x = self._expr_uses_trig_of(cx_src, dep_vars)
        trig_y = self._expr_uses_trig_of(cy_src, dep_vars)
        if trig_x or trig_y:
            R_expr  = self._extract_trig_amplitude(cx_src, cy_src)
            offsets = self._extract_trig_offsets(cx_src, cy_src, dep_vars)
            r_grows = (any(v in cx_src for v in dep_vars) and not trig_x) or \
                      (any(v in cy_src for v in dep_vars) and not trig_y)
            lt = 'Spirale' if r_grows else 'Cercle'
            return (lt, {'R_expr': R_expr or '', 'N_expr': range_info[1],
                         'cx_src': cx_src, 'cy_src': cy_src, **offsets})
        var_in_x = loop_var in cx_src
        var_in_y = loop_var in cy_src
        if var_in_x or var_in_y:
            dx_expr = self._extract_linear_step(cx_src, loop_var) if var_in_x else '0'
            dy_expr = self._extract_linear_step(cy_src, loop_var) if var_in_y else '0'
            direction = ('x' if var_in_x and not var_in_y else
                         'y' if var_in_y and not var_in_x else 'diag')
            return ('Ligne', {'direction': direction, 'dx_expr': dx_expr,
                              'dy_expr': dy_expr, 'cx_src': cx_src, 'cy_src': cy_src})
        return ('Générique', {'cx_src': cx_src, 'cy_src': cy_src})

    def _extract_center_exprs(self, call_node) -> Optional[Tuple[str, str]]:
        for kw in call_node.keywords:
            if kw.arg == 'center':
                v = kw.value
                if isinstance(v, ast.List) and len(v.elts) >= 2:
                    return (self._unparse(v.elts[0]), self._unparse(v.elts[1]))
        return None

    def _expr_uses_trig_of(self, expr: str, dep_vars) -> bool:
        if 'cos' not in expr and 'sin' not in expr:
            return False
        return any(v in expr for v in dep_vars)

    def _extract_trig_amplitude(self, cx_src: str, cy_src: str) -> Optional[str]:
        for expr in (cx_src, cy_src):
            if 'cos' not in expr and 'sin' not in expr:
                continue
            try:
                tree = ast.parse(expr, mode='eval')
                for node in ast.walk(tree):
                    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                        for a_side, b_side in ((node.left, node.right),
                                               (node.right, node.left)):
                            if not isinstance(b_side, ast.Call):
                                continue
                            func = b_side.func
                            fname = (func.attr if isinstance(func, ast.Attribute)
                                     else func.id if isinstance(func, ast.Name) else None)
                            if fname in ('cos', 'sin'):
                                return self._unparse(a_side)
            except Exception:
                pass
        return None

    def _extract_trig_offsets(self, cx_src: str, cy_src: str, dep_vars) -> dict:
        if isinstance(dep_vars, str):
            dep_vars = {dep_vars}
        result: dict = {}
        for key, expr in (('offset_x', cx_src), ('offset_y', cy_src)):
            if 'cos' not in expr and 'sin' not in expr:
                continue
            try:
                tree = ast.parse(expr, mode='eval')
                for node in ast.walk(tree):
                    if isinstance(node, ast.BinOp) and isinstance(
                        node.op, (ast.Add, ast.Sub)
                    ):
                        for side in (node.left, node.right):
                            s = self._unparse(side)
                            if ('cos' not in s and 'sin' not in s
                                    and not any(v in s for v in dep_vars)):
                                result[key] = s
                                break
            except Exception:
                pass
        return result

    def _extract_linear_step(self, expr: str, loop_var: str) -> str:
        try:
            tree = ast.parse(expr, mode='eval')
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                    ls, rs = self._unparse(node.left), self._unparse(node.right)
                    if ls == loop_var: return rs
                    if rs == loop_var: return ls
        except Exception:
            pass
        return ''

    def _extract_step_in_body(self, loop_var: str, body: list, axis: int = 0) -> str:
        for call in self._iter_avatar_calls(body):
            ce = self._extract_center_exprs(call)
            if ce is not None:
                step = self._extract_linear_step(ce[axis], loop_var)
                if step:
                    return step
        return ''

    def _build_template(self, call_node, loop_var: str) -> dict:
        cfg: dict = {}
        if isinstance(call_node.func, ast.Attribute):
            cfg['avatar_type'] = call_node.func.attr
        params: dict = {}
        for kw in call_node.keywords:
            if kw.arg is None:
                continue
            literal = self._try_literal(kw.value)
            if literal is not None:
                params[kw.arg] = {'value': literal, 'is_expr': False}
            else:
                expr = self._unparse(kw.value)
                params[kw.arg] = {'expr': expr, 'uses_loop_var': loop_var in expr, 'is_expr': True}
        cfg['params'] = params
        return cfg

    def _detect_group(self, body: list) -> Optional[str]:
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name not in self.STD_CONTAINERS:
                    return name
            elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
                c = node.value
                if (isinstance(c.func, ast.Attribute)
                        and c.func.attr in ('addAvatar', 'append', 'extend')
                        and isinstance(c.func.value, ast.Name)):
                    name = c.func.value.id
                    if name not in self.STD_CONTAINERS:
                        return name
        return None

    def _resolve_int(self, expr: str) -> Optional[int]:
        try:
            val = ast.literal_eval(expr)
            if isinstance(val, (int, float)): return int(val)
        except (ValueError, TypeError): pass
        try:
            val = eval(expr, {'__builtins__': {}}, dict(self.dynamic_vars))
            if isinstance(val, (int, float)): return int(val)
        except Exception: pass
        return None

    def _resolve_float(self, expr: str) -> Optional[float]:
        if not expr: return None
        try:
            val = ast.literal_eval(expr)
            if isinstance(val, (int, float)): return float(val)
        except (ValueError, TypeError): pass
        try:
            val = eval(expr, {'__builtins__': {}}, dict(self.dynamic_vars))
            if isinstance(val, (int, float)): return float(val)
        except Exception: pass
        return None

    def _try_literal(self, node) -> Any:
        try: return ast.literal_eval(node)
        except (ValueError, TypeError): return None

    @staticmethod
    def _unparse(node) -> str:
        try:
            return ast.unparse(node)
        except AttributeError:
            pass
        try:
            import astunparse  # type: ignore[import]
            return astunparse.unparse(node).strip()
        except Exception:
            return '<expr>'
