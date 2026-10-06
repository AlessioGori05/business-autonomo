"""Risposte d'esempio per la modalità demo (nessuna AI, nessun account). Servono solo a provare la catena."""
import itertools
import random

_TITLES = itertools.cycle([
    "Honey never spoils", "Why octopuses have three hearts", "The fastest way to peel garlic", "Your phone has a hidden ruler",
    "Bananas are berries, strawberries are not", "Sharks existed before trees", "The two-minute rule for chores",
    "Why cold water boils slower", "Sloths can hold their breath long", "How to fold a fitted sheet",
    "The Eiffel Tower grows in summer", "A day on Venus is longer than its year", "Cats can't taste sweetness",
    "Wombat poop is cube shaped", "Freeze ginger for easy grating", "Rubber bands open stuck jars"])


def fake_ask_json(system, user, temperature=None):
    it = "Language: Italian" in user
    r = random.randint(100, 999)
    if "t-shirt/mug designs" in user:
        base = (["Caffè prima, parole dopo", "Introverso ma connesso", "Il mio cane è il capo", "Compilo quindi sono"]
                if it else ["Coffee first, words later", "Introvert but online", "My dog is the boss", "I compile therefore I am"])
        return [{"slogan": s, "audience": "demo", "listing_title": s, "tags": ["demo"] * 3, "description": "Demo."} for s in base]
    if "mini-guide" in user:
        return {"title": ("Guida demo al risparmio" if it else "Demo saving guide") + f" {r}", "subtitle": "Demo",
                "intro": "Testo introduttivo di esempio. " * 6,
                "chapters": [{"heading": f"Capitolo {i}", "tips": ["Consiglio pratico di esempio, breve e utile."] * 4} for i in range(1, 6)],
                "checklist": ["Voce di checklist"] * 7,
                "emails": [{"subject": f"Email {i}", "body": "Corpo email di esempio."} for i in range(1, 5)]}
    if "animal" in user and "toddlers" in system:
        return {"animal": "elefante" if it else "elephant", "title": ("L'elefante" if it else "The elephant") + f" {r}",
                "lines": (["Ecco l'elefante!", "È molto grande.", "Ha una lunga proboscide.", "Beve con la proboscide.",
                           "Ha grandi orecchie.", "Ciao elefante!"] if it else
                          ["Here is the elephant!", "It is very big.", "It has a long trunk.", "It drinks with its trunk.",
                           "It has big ears.", "Bye bye elephant!"]), "facts_confidence": 0.95}
    lines_it = ["Lo sapevi che il miele non scade praticamente mai?", "Nelle tombe egizie ne hanno trovato di commestibile.",
                "Il segreto è la pochissima acqua che contiene.", "E la sua acidità naturale.", "I batteri non riescono a sopravvivere.",
                "Conservalo chiuso e lontano dall'umidità.", "Link nel profilo per la lista completa"]
    lines_en = ["Did you know honey basically never spoils?", "Edible honey was found in ancient Egyptian tombs.",
                "The secret is its very low water content.", "Plus its natural acidity.", "Bacteria simply can't survive in it.",
                "Keep it sealed and away from moisture.", "Link in bio for the full list"]
    words = "honey octopus garlic phone ruler banana shark chores water sloth sheet tower venus cat ginger jar moon salt lemon brain".split()
    data = {"title": " ".join(random.sample(words, 5)).capitalize(),
            "lines": lines_it if it else lines_en, "description": "Demo.", "tags": ["demo", "facts", "shorts"],
            "facts_confidence": 0.95}
    if "products" in user:
        data["page_intro"] = "Introduzione di esempio alla selezione." if it else "Example introduction to the picks."
        data["products"] = [{"name": n, "search_query": n, "why": "Esempio." if it else "Example.",
                             "check_before_buying": "Esempio." if it else "Example."}
                            for n in (["lampada da scrivania", "supporto per laptop", "tappetino per mouse"] if it else
                                      ["desk lamp", "laptop stand", "mouse pad"])]
    return data
