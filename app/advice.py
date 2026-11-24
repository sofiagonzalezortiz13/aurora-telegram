import re
import unicodedata

TOPIC_ICONS = {
    "Cabello": "💇", "Cejas": "✏️", "Ropa": "👕", "Joyería": "💍",
    "Maquillaje": "💄", "Barba": "🪒", "Piercings": "✨",
    "Base y corrector": "🧴", "Mejillas": "🌸", "Ojos": "👁️", "Labios": "💋",
}

SHAPES = {
    "Ovalado": ("capas suaves o un corte con textura", "barba corta siguiendo la mandíbula",
                "rubor desde las manzanas hacia las sienes", "una ceja con arco suave", "cuello redondo"),
    "Redondo": ("capas largas o laterales cortos con volumen arriba", "perilla o barba más larga en el mentón",
                "rubor diagonal hacia las sienes", "una ceja con arco definido", "escote en V"),
    "Cuadrado": ("ondas suaves o un corte con textura y raya lateral", "barba redondeada en los ángulos",
                 "contorno difuminado en las esquinas de la mandíbula", "una ceja suavemente curvada", "cuello ovalado"),
    "Corazón/triángulo invertido": ("capas a la altura de la mandíbula o flequillo lateral",
                                  "barba corta con plenitud en la mandíbula", "rubor centrado en las mejillas",
                                  "una ceja con arco bajo", "cuello barco"),
    "Alargado/rectangular": ("flequillo lateral o volumen en los costados", "barba corta en el mentón",
                            "rubor en sentido horizontal", "una ceja ligeramente recta", "cuello cerrado"),
    "Diamante": ("flequillo lateral o volumen a la altura de la mandíbula", "barba corta con laterales llenos",
                 "rubor suave sobre la parte frontal de las mejillas", "una ceja de curva suave", "escote ovalado"),
}
SEASON_STYLE = {
    "Primavera": ("coral suave", "miel o cobrizo claro", "oro amarillo"),
    "Verano": ("malva", "castaño ceniza", "plata"),
    "Otoño": ("terracota", "castaño cobrizo", "oro envejecido"),
    "Invierno": ("ciruela fría", "castaño espresso frío", "plata brillante"),
}
MAKEUP_COLORS = {
    "Primavera": ("champán dorado y marrón miel", "durazno o coral claro", "champán cálido"),
    "Verano": ("topo frío y malva", "rosa empolvado o malva", "perla suave"),
    "Otoño": ("bronce y oliva apagado", "terracota suave o canela", "dorado suave"),
    "Invierno": ("topo frío y ciruela", "rosa frío o cereza", "perla fría"),
}
MAKEUP_WORDS = {
    "Base y corrector": {"base", "corrector", "ojeras", "polvo", "polvos", "cobertura"},
    "Mejillas": {"rubor", "blush", "colorete", "contorno", "bronceador", "iluminador"},
    "Ojos": {"ojos", "sombra", "sombras", "delineador", "delineado", "rimel", "mascara", "pestanas"},
    "Labios": {"labios", "labial", "pintalabios", "gloss"},
}
HAIRCUT_DETAILS = {
    "Ovalado": "Para pelo largo, pide capas desde el pómulo; para corto, textura suave arriba.",
    "Redondo": "Para pelo largo, empieza las capas debajo del mentón; para corto, deja altura arriba y menos volumen en las sienes.",
    "Cuadrado": "Marca la raya a un lado y deja que las ondas empiecen debajo del pómulo. Para pelo corto, pide un acabado con tijera alrededor de las sienes.",
    "Corazón/triángulo invertido": "Lleva el volumen a la altura de la mandíbula con capas o puntas hacia fuera. Si prefieres flequillo, llévalo de lado.",
    "Alargado/rectangular": "Pide textura a la altura de las sienes y poco volumen en la coronilla. Un flequillo lateral puede equilibrar la frente.",
    "Diamante": "Prueba un flequillo de lado y capas a la altura del mentón para dar volumen debajo del pómulo.",
}
MASCULINE_STYLES = {
    "Ovalado": (
        "Pide los lados un poco más cortos y deja arriba lo justo para peinarlo de lado.",
        "Si usas barba, llévala corta y pareja. Recorta los pelitos sueltos del cuello.",
        "Si prefieres algo más fácil de peinar, pide un corte corto con tijera y déjalo caer como crece.",
    ),
    "Redondo": (
        "Pide los lados cortos y deja algo de largo arriba. Peina el frente un poco hacia arriba para que el rostro se vea más alargado.",
        "Si usas barba, recorta más las mejillas y deja el mentón un poco más largo. Así no concentras el volumen a los lados.",
        "Si no te gusta levantar el pelo, péinalo de lado y mantén los lados pegados.",
    ),
    "Cuadrado": (
        "Pide un corte con tijera, con los lados un poco más cortos. Peina el frente de lado y deja que el pelo caiga natural.",
        "Si usas barba, déjala corta y redondea un poco las esquinas de la mandíbula al recortarla.",
        "Si lo quieres más corto, pide que rebajen solo alrededor de las orejas y la nuca.",
    ),
    "Corazón/triángulo invertido": (
        "Pide un corte a tijera con la parte de arriba a media altura. Péinala de lado y deja algo de pelo alrededor de las sienes.",
        "Si te crece bien la barba en la mandíbula, deja un poco de largo ahí para darle más presencia a la parte baja de la cara.",
        "Si te gusta llevar el pelo más corto, pide que rebajen solo la nuca y alrededor de las orejas. Peina la parte de arriba hacia atrás con los dedos.",
    ),
    "Alargado/rectangular": (
        "Pide que dejen algo de pelo en los lados y que recorten la parte de arriba con tijera. Péinala de lado, cerca de la cabeza, para equilibrar el largo de la cara.",
        "Si usas barba, mantén el mentón corto y deja algo de barba en las mejillas para que la cara no se vea más larga.",
        "Si prefieres algo más corto, pide un corte parejo a tijera y acomódalo con los dedos siguiendo la caída del pelo.",
    ),
    "Diamante": (
        "Pide los lados a tijera, con algo de largo cerca de las sienes. Deja el frente un poco más largo para peinarlo de lado.",
        "Si usas barba, deja un poco de largo a los lados de la mandíbula y mantén el mentón corto.",
        "Si prefieres llevarlo hacia atrás, péinalo con los dedos y deja los lados naturales.",
    ),
}
MASCULINE_OUTFITS = {
    "Primavera": (
        "Para diario, prueba una camiseta marfil, un jean azul claro y tenis blancos.",
        "Si te quieres arreglar más, ponte una camisa turquesa suave con pantalón beige y mocasines café.",
    ),
    "Verano": (
        "Para diario, combina un polo azul humo con pantalón gris claro y tenis blancos.",
        "Si te quieres arreglar más, prueba una camisa lavanda con pantalón azul marino y zapatos café oscuro.",
    ),
    "Otoño": (
        "Para diario, ponte una sobrecamisa oliva sobre una camiseta cruda, con jean oscuro y botas café.",
        "Si te quieres arreglar más, combina una camisa terracota con pantalón camel y mocasines café.",
    ),
    "Invierno": (
        "Para diario, prueba una camiseta blanco óptico con chaqueta azul cobalto, jean negro y tenis blancos.",
        "Si te quieres arreglar más, combina una camisa borgoña con pantalón gris carbón y zapatos negros.",
    ),
}
MASCULINE_OUTFIT_FALLBACK = (
    "Para diario, prueba una camiseta gris, un jean azul recto y tenis blancos.",
    "Si te quieres arreglar más, ponte una camisa azul marino con pantalón beige y zapatos café.",
)
OCCASIONS = {
    "entrevista": ({"entrevista", "laboral", "oficina", "trabajo", "formal"},
                   "Para la entrevista, usa una prenda lisa cerca del rostro y un peinado que puedas acomodar sin tocarlo constantemente."),
    "diario": ({"diario", "casual", "cotidiano", "rapido", "rapida"},
               "Para diario, empieza por un solo color de la paleta y un peinado que puedas rehacer en cinco minutos."),
    "evento": ({"fiesta", "boda", "noche", "evento", "cita"},
               "Para el evento, elige una prenda de la paleta como protagonista y repite el acabado metálico en uno o dos accesorios."),
}
MASCULINE_OCCASION_TIPS = {
    "entrevista": "Para una entrevista, lleva la camisa por dentro y usa un cinturón del mismo color que los zapatos.",
    "diario": "Si llevas camisa o sobrecamisa, puedes subir un poco las mangas para que se vea más relajado.",
    "evento": "Si la invitación pide ropa formal, añade un saco liso.",
}


def recommendations(profile, mode):
    shape = profile["forma"]
    _, beard, _, brow, collar = SHAPES[shape]
    _, dye, metal = SEASON_STYLE.get(profile["estacion"], {
        "calido": ("", "castaño dorado", "oro amarillo"),
        "frio": ("", "castaño ceniza", "plata"),
    }.get(normalize(profile["subtono"]), ("", "un tono cercano al actual", "plata u oro suave")))
    palette = profile["paleta"]
    if mode == "masculino":
        haircut, beard, _ = MASCULINE_STYLES[shape]
        outfits = MASCULINE_OUTFITS.get(profile["estacion"], MASCULINE_OUTFIT_FALLBACK)
        return {
            "Cabello": haircut,
            "Barba": beard + " Si te crece dispareja, prueba una barba de uno o dos días o aféitate.",
            "Cejas": "Péinalas con un cepillito. Si quieres limpiarlas, quita solo los pelitos sueltos entre las cejas.",
            "Ropa": " ".join(outfits),
            "Joyería": f"Si usas accesorios, empieza con un reloj o una cadena fina. Busca un acabado en {metal}.",
            "Piercings": "Si ya tienes perforado el lóbulo y quieres algo discreto, prueba un arete pequeño del mismo color que el reloj o la cadena.",
        }
    outfit = (f"Combina {palette[0]} cerca del rostro con {palette[1]} en una segunda prenda."
              if len(palette) >= 2 else
              "Compara dos prendas lisas cerca del rostro con luz natural.")
    entries = {
        "Cabello": HAIRCUT_DETAILS[shape],
        "Cejas": f"Prueba {brow}. Péinala hacia arriba y rellena solo los huecos con trazos finos siguiendo el pelo.",
        "Ropa": f"Prueba {collar}. {outfit}",
        "Joyería": f"Prueba {metal} en un arete pequeño o una cadena fina. Repite el acabado si combinas ambas piezas.",
    }
    if mode in ("femenino", "neutro"):
        entries["Maquillaje"] = "\n" + "\n".join(
            f"{TOPIC_ICONS[part]} {part} · {tip}"
            for part, tip in makeup_recommendations(profile).items()
        )
        entries["Cabello"] += f" Si quieres probar {dye}, empieza con mechones finos alrededor del rostro."
    if mode == "neutro":
        entries["Barba"] = f"Prueba {beard}. Empieza con una guía de 4 mm y baja a 2 mm donde quieras quitar volumen."
        entries["Piercings"] = f"Para un detalle discreto, prueba un botón pequeño en el lóbulo con acabado tipo {metal}. Si prefieres el hélix, un perforador puede valorar la ubicación y el ajuste."
    return entries


def normalize(message):
    return "".join(c for c in unicodedata.normalize("NFKD", message.casefold())
                   if not unicodedata.combining(c))


def makeup_recommendations(profile):
    season = profile["estacion"]
    undertone = normalize(profile["subtono"])
    placement = SHAPES[profile["forma"]][2]
    blush, _, _ = SEASON_STYLE.get(season, {
        "calido": ("melocotón suave", "", ""),
        "frio": ("rosa malva", "", ""),
    }.get(undertone, ("rosa neutro", "", "")))
    shadows, lips, highlight = MAKEUP_COLORS.get(season, {
        "calido": ("beige cálido y cobre suave", "durazno o rosa cálido", "champán cálido"),
        "frio": ("topo frío y malva", "rosa frío o malva", "perla suave"),
    }.get(undertone, ("beige neutro y marrón suave", "rosa neutro o beige rosado", "champán neutro")))
    return {
        "Base y corrector": (
            f"Busca una base de subtono {profile['subtono'].lower()}. "
            "Prueba dos tonos en la mandíbula con luz natural y espera unos minutos antes de elegir. "
            "Aplica una capa fina desde el centro del rostro y pon un punto de corrector en la parte más oscura de la ojera. "
            "Sella solo las zonas con brillo si lo necesitas."
        ),
        "Mejillas": (
            f"Prueba {placement}. Usa rubor {blush} y difumina en capas finas. "
            f"Si quieres luminosidad, pon un toque {highlight} sobre el punto alto del pómulo."
        ),
        "Ojos": (
            f"Prueba sombras en {shadows}. Usa el tono claro en el párpado móvil y concentra el oscuro en el tercio externo. "
            "Para definir, traza una línea fina a ras de las pestañas superiores y aplica una capa de máscara."
        ),
        "Labios": (
            f"Prueba {lips}. Para diario, difumina una capa con el dedo. "
            "Para un acabado definido, perfila con un lápiz de tono parecido al labial y rellena desde el centro."
        ),
    }


def reply(profile, mode, message, previous):
    words = set(re.findall(r"[a-z]+", normalize(message)))
    entries = recommendations(profile, mode)
    matches = {
        "Cabello": {"corte", "cortes", "cabello", "pelo", "peinado", "tinte", "coloracion", "flequillo", "capas", "mechas", "degradado", "patillas"},
        "Cejas": {"ceja", "cejas", "slit", "slits"},
        "Ropa": {"color", "colores", "paleta", "ropa", "escote", "camisa", "camiseta", "polo", "jean", "tenis", "blusa", "vestido", "outfit", "conjunto"},
        "Joyería": {"joyeria", "joya", "metal", "arete", "aretes", "cadena", "collar", "oro", "plata"},
        "Maquillaje": {"maquillaje"} | set().union(*MAKEUP_WORDS.values()),
        "Barba": {"barba", "bigote", "perilla", "afeito", "afeitar", "afeitado"},
        "Piercings": {"piercing", "piercings", "helix", "lobulo"},
    }
    topics = [topic for topic, terms in matches.items() if terms & words]
    occasion = next((key for key, (terms, _) in OCCASIONS.items() if terms & words), None)
    alternative = bool(words & {"otra", "otro", "opcion", "alternativa"})
    if not topics and (occasion or alternative or "eso" in words):
        topics = previous or ["Cabello", "Ropa"]
    if not topics:
        return "Puedo usar tu informe para hablar de " + ", ".join(entries).lower() + ".", previous
    selected = [(topic, entries[topic]) for topic in topics if topic in entries]
    if not selected:
        return "Esa categoría está disponible en otro modo. Prueba el modo neutro para ver todas.", previous
    context = "Yo probaría esto" if mode == "masculino" else f"Para tu rostro {profile['forma'].lower()}"
    if profile["estacion"] and mode != "masculino":
        context += f" y la estimación de {profile['estacion'].lower()}"
    if alternative:
        options = {
            "Cabello": f"Si buscas otra opción, prueba {SHAPES[profile['forma']][0]} antes de decidir cuánto largo cortar.",
            "Ropa": "Prueba un segundo color de la paleta en la prenda superior y deja el resto del conjunto en tonos neutros.",
            "Cejas": "Prueba gel transparente para definir la forma sin añadir color.",
            "Joyería": "Prueba una sola pieza, como un aro fino o un anillo liso.",
            "Maquillaje": "Prueba el mismo tono en crema y aplícalo dando toques con los dedos.",
            "Barba": "Para un cambio más discreto, usa una guía uniforme de 2 mm y limpia el cuello.",
            "Piercings": "Prueba un aro de presión para ver cómo queda el accesorio antes de perforarte.",
        }
        if mode == "masculino":
            options.update(
                Cabello=MASCULINE_STYLES[profile["forma"]][2],
                Ropa=MASCULINE_OUTFITS.get(profile["estacion"], MASCULINE_OUTFIT_FALLBACK)[1],
                Barba="Si quieres algo fácil de mantener, prueba una barba corta y pareja. Si tienes pocos pelitos, también puedes afeitarte.",
            )
        selected = [(topic, options[topic]) for topic, _ in selected]
    elif "Maquillaje" in topics and "Maquillaje" in entries:
        parts = [part for part, terms in MAKEUP_WORDS.items() if terms & words]
        if {"labios", "labial"} & words and words & MAKEUP_WORDS["Ojos"] == {"delineador"}:
            parts.remove("Ojos")
        if parts:
            makeup = makeup_recommendations(profile)
            selected = [(topic, tip) for topic, tip in selected if topic != "Maquillaje"]
            selected.extend((part, makeup[part]) for part in parts)
    if mode == "masculino" and occasion and not alternative:
        outfits = MASCULINE_OUTFITS.get(profile["estacion"], MASCULINE_OUTFIT_FALLBACK)
        outfit = outfits[0 if occasion == "diario" else 1]
        selected = [(topic, outfit if topic == "Ropa" else tip) for topic, tip in selected]
    lines = [context + ".", "", *(f"{TOPIC_ICONS[topic]} {topic} · {tip}" for topic, tip in selected)]
    if occasion:
        tip = MASCULINE_OCCASION_TIPS[occasion] if mode == "masculino" else OCCASIONS[occasion][1]
        lines.extend(("", tip))
    return "\n".join(lines), [topic for topic in topics if topic in entries]
