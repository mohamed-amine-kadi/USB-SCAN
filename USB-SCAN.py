# Bibliothèque standard pour ouvrir un navigateur par défaut
import webbrowser

# Liste pour stocker les réponses
reponses_utilisateur = []

continu = True

while continu:
    # Demander le nom de l'utilisateur
    nom = input("Quel est votre nom ? ")

    # Afficher le message de bienvenue
    print(f"Bonjour, {nom} !")

    # Demander si l'utilisateur souhaite continuer
    reponse = input("Souhaitez-vous continuer ? (oui/non) ").strip().lower()

    # Stocker la réponse
    reponses_utilisateur.append({"nom": nom, "reponse": reponse})

    if reponse != "oui":
        continu = False
        print("Au revoir !")

# Générer le contenu HTML
contenu_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Réponses de l'utilisateur</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 50%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Historique des réponses</h1>
    <table>
        <tr>
            <th>Nom</th>
            <th>Réponse</th>
        </tr>
"""

# Ajouter les réponses au HTML
for reponse in reponses_utilisateur:
    contenu_html += f"""
        <tr>
            <td>{reponse['nom']}</td>
            <td>{reponse['reponse']}</td>
        </tr>
    """

# Fermer le HTML
contenu_html += """
    </table>
</body>
</html>
"""

# Écrire le contenu dans un fichier HTML
with open("reponses_utilisateur.html", "w", encoding="utf-8") as fichier:
    fichier.write(contenu_html)

# Ouvrir le fichier dans le navigateur
webbrowser.open("reponses_utilisateur.html")

