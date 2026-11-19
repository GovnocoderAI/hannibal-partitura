from story.content import NODES, START, ENDINGS


def validate():
    errors = []
    if START not in NODES:
        errors.append("нет стартовой ноды: " + START)
    for nid, node in NODES.items():
        nxt = node.get("next")
        if nxt is not None and nxt not in NODES:
            errors.append(f"{nid}: next -> {nxt} не существует")
        if nxt is None and not node.get("ending") and not node.get("choices"):
            errors.append(f"{nid}: тупик без концовки")
        for i, ch in enumerate(node.get("choices", [])):
            goto = ch.get("goto")
            if goto and goto not in NODES:
                errors.append(f"{nid}#{i}: goto -> {goto} не существует")
            if not goto and not node.get("ending") and not node.get("next"):
                errors.append(f"{nid}#{i}: выбор никуда не ведёт")
            if not ch.get("text"):
                errors.append(f"{nid}#{i}: пустой текст выбора")
        for j, rule in enumerate(node.get("goto_if", [])):
            g = rule.get("goto")
            if g and g not in NODES:
                errors.append(f"{nid}: goto_if[{j}] -> {g} не существует")
        for eff in [node.get("effects", {})] + [c.get("effects", {}) for c in node.get("choices", [])]:
            for f in eff.get("flags", []):
                if not isinstance(f, str):
                    errors.append(f"{nid}: флаг не строка")
    reachable = set()
    stack = [START]
    while stack:
        nid = stack.pop()
        if nid in reachable or nid not in NODES:
            continue
        reachable.add(nid)
        node = NODES[nid]
        if node.get("next"):
            stack.append(node["next"])
        for ch in node.get("choices", []):
            if ch.get("goto"):
                stack.append(ch["goto"])
        for rule in node.get("goto_if", []):
            if rule.get("goto"):
                stack.append(rule["goto"])
    for nid in NODES:
        if nid not in reachable:
            errors.append(f"{nid}: недостижимая нода")
    found = {n.get("ending") for n in NODES.values() if n.get("ending")}
    for eid in ENDINGS:
        if eid not in found:
            errors.append(f"концовка {eid} недостижима")
    for eid in found:
        if eid not in ENDINGS:
            errors.append(f"концовка {eid} не описана в ENDINGS")
    return errors
