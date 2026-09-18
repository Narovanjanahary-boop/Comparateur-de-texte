import os
import re
import io
import difflib
import datetime

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False


app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024 #25Mo taille max = 25 Mo

INFOS_AUTEUR = """Analyseur de Textes Comparatif

Auteur : NAROVANJANAHARY Solofoniaina Ferdinand
Etudiant : 1ère année de Licence Informatique à l'EMIT Fianarantsoa (DA2I)
E-mail : rovaferdinand844@gmail.com
Whatsapp : +261383167780
Dernière mise à jour : 2026
"""


def lire_texte_dun_fichier(donnees_binaires, nom_fichier): #Lire les fichiers

    _, extension = os.path.splitext(nom_fichier) #Recupérer extension
    extension = extension.lower()

    if extension in (".txt", ".rtf", ".md", ".csv"): #texte simple
        return decoder_texte(donnees_binaires)

    if extension == ".pdf": #pdf
        return lire_pdf(donnees_binaires)

    if extension == ".docx": #word
        return lire_docx(donnees_binaires)

    if extension == ".doc": #ancien format
        raise RuntimeError(
            "Le format .doc ancien n'est pas pris en charge. "
            "Convertissez le fichier en .docx ou en .txt."
        )

    return decoder_texte(donnees_binaires) #Decoder encore un fichier inconnu


def decoder_texte(donnees_binaires):
    encodages_possibles = ["utf-8", "latin-1", "cp1252"] #Octet en texte avec plusieurs encodages

    for encodage in encodages_possibles:
        try:
            return donnees_binaires.decode(encodage)
        except UnicodeDecodeError:
            continue #Encodage raté,passer au suivant

    return donnees_binaires.decode("utf-8", errors="ignore") #Pour ignorer les caractères impossibles à lire


def lire_pdf(donnees_binaires): #excration du pdf
    if PyPDF2 is None:
        raise RuntimeError(
            "Le module PyPDF2 n'est pas installé. "
            "Installez-le avec : pip install PyPDF2"
        )

    fichier_pdf = PyPDF2.PdfReader(io.BytesIO(donnees_binaires))

    texte_complet = ""
    for page in fichier_pdf.pages:
        texte_de_la_page = page.extract_text()
        if texte_de_la_page:
            texte_complet += texte_de_la_page + "\n"

    return texte_complet


def lire_docx(donnees_binaires): #extraction docx
    if docx is None:
        raise RuntimeError(
            "Le module python-docx n'est pas installé. "
            "Installez-le avec : pip install python-docx"
        )

    document = docx.Document(io.BytesIO(donnees_binaires))

    lignes = []
    for paragraphe in document.paragraphs:
        lignes.append(paragraphe.text)

    return "\n".join(lignes)





#COMPARAISON DES TEXTES

def decouper_en_mots(texte): #Découper les textes en listes des mots
    resultat = []
    for correspondance in re.finditer(r"\S+", texte):
        resultat.append(correspondance.group(0))
    return resultat


def comparer_deux_textes(texte_1, texte_2): #Comparer 2 textes mots par mots et retourner les stats utilses (en forme de dict)
    mots_1 = decouper_en_mots(texte_1)
    mots_2 = decouper_en_mots(texte_2)
    # deux listes et dire ce qui a été ajouté / supprimé / modifié
    comparateur = difflib.SequenceMatcher(None, mots_1, mots_2) #SequenceMatcher : sait comparer

    similitude = round(comparateur.ratio() * 100, 1)

    # Mots communs aux deux textes
    ensemble_1 = set(mots_1)
    ensemble_2 = set(mots_2)
    mots_communs = ensemble_1 & ensemble_2
    tous_les_mots = ensemble_1 | ensemble_2

    if len(tous_les_mots) > 0:
        pourcentage_identique = round(len(mots_communs) / len(tous_les_mots) * 100, 1)
    else:
        pourcentage_identique = 0.0

    pourcentage_different = round(100 - pourcentage_identique, 1)

    return {
        "pourcentage_identique": pourcentage_identique,
        "pourcentage_similitude": similitude,
        "pourcentage_different": pourcentage_different,
        "nombre_mots_1": len(mots_1),
        "nombre_mots_2": len(mots_2),
        "operations": comparateur.get_opcodes(),
    }


def classer_les_mots(operations):

#2 dict pour stocker la position et nature du mot(modifie,différent) veant du resultat du difflib
    classes_texte_1 = {}
    classes_texte_2 = {}

    for operation in operations:
        type_operation, debut_1, fin_1, debut_2, fin_2 = operation

        if type_operation == "replace":
            for i in range(debut_1, fin_1):
                classes_texte_1[i] = "mot_modifie"
            for j in range(debut_2, fin_2):
                classes_texte_2[j] = "mot_modifie"

        elif type_operation == "delete":
            for i in range(debut_1, fin_1):
                classes_texte_1[i] = "mot_different"

        elif type_operation == "insert":
            for j in range(debut_2, fin_2):
                classes_texte_2[j] = "mot_different"

    return classes_texte_1, classes_texte_2




#PAGE ET ROUTE

@app.route("/")
def page_accueil():
    """Affiche la page principale de l'application."""
    return render_template("index.html")


@app.post("/api/analyse")
def api_analyse(): #Recoit les 2 textes ou fichiers envoyés par le navigateur,comparer et renvoyer results
    texte_1 = request.form.get("texte1", "")
    texte_2 = request.form.get("texte2", "")

    # Si un fichier a été envoyé, on lit son contenu à la place du texte collé
    fichier_1 = request.files.get("fichier1")
    if fichier_1 and fichier_1.filename:
        donnees = fichier_1.read()
        texte_1 = lire_texte_dun_fichier(donnees, fichier_1.filename)

    fichier_2 = request.files.get("fichier2")
    if fichier_2 and fichier_2.filename:
        donnees = fichier_2.read()
        texte_2 = lire_texte_dun_fichier(donnees, fichier_2.filename)

    if texte_1.strip() == "" or texte_2.strip() == "":
        message_erreur = "Collez ou importez du texte dans les deux cases avant de lancer l'analyse."
        return jsonify(error=message_erreur), 400

    resultat = comparer_deux_textes(texte_1, texte_2)
    classes_1, classes_2 = classer_les_mots(resultat["operations"])

    reponse = {
        "stats": {
            "pourcentage_identique": resultat["pourcentage_identique"],
            "pourcentage_similitude": resultat["pourcentage_similitude"],
            "pourcentage_different": resultat["pourcentage_different"],
            "nombre_mots_1": resultat["nombre_mots_1"],
            "nombre_mots_2": resultat["nombre_mots_2"],
        },
        "classes1": classes_1,
        "classes2": classes_2,
        "operations": resultat["operations"],
    }

    return jsonify(reponse)


@app.post("/api/fichier")
def api_fichier(): #Recoit un seul fichier venant du bouton parcourir

    fichier = request.files.get("file")
    if not fichier or not fichier.filename:
        return jsonify(error="Aucun fichier sélectionné."), 400

    donnees = fichier.read()

    try:
        texte = lire_texte_dun_fichier(donnees, fichier.filename)
    except Exception as erreur:
        return jsonify(error=str(erreur)), 400

    nom_extension = os.path.splitext(fichier.filename)[1].upper().lstrip(".")

    return jsonify(
        filename=secure_filename(fichier.filename),
        text=texte,
        size=len(donnees),
        extension=nom_extension,
    )


@app.post("/api/recherche")
def api_recherche(): #Chercher un mot et renvoie sa position
    donnees_recues = request.json
    mot_recherche = donnees_recues.get("mot", "")
    textes = donnees_recues.get("texts", ["", ""])

    if mot_recherche == "":
        return jsonify(total=0, occurrences=[[], []])

    toutes_les_occurrences = []
    nombre_total = 0

    for texte in textes:
        occurrences_pour_ce_texte = []

        for correspondance in re.finditer(re.escape(mot_recherche), texte, flags=re.IGNORECASE):
            occurrences_pour_ce_texte.append([correspondance.start(), correspondance.end()])
            nombre_total += 1

        toutes_les_occurrences.append(occurrences_pour_ce_texte)

    return jsonify(total=nombre_total, occurrences=toutes_les_occurrences)


@app.post("/api/pdf")
def api_pdf(): #Créer pdf avec les resultats d'analyse et renvoie à télecharger
    if not REPORTLAB_DISPONIBLE:
        message = "Le module reportlab n'est pas installé. Installez-le avec : pip install reportlab"
        return jsonify(error=message), 400

    donnees = request.json
    memoire_tampon = io.BytesIO()

    document_pdf = canvas.Canvas(memoire_tampon, pagesize=A4)
    largeur_page, hauteur_page = A4
    marge = 2 * 72
    position_y = hauteur_page - marge

    #Titre de document
    document_pdf.setFont("Helvetica-Bold", 16)
    document_pdf.drawString(marge, position_y, "Rapport d'analyse comparative de textes")
    position_y -= 28

    #Date
    date_du_jour = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    document_pdf.setFont("Helvetica", 9)
    document_pdf.setFillColor(colors.grey)
    document_pdf.drawString(marge, position_y, "Généré le " + date_du_jour)
    document_pdf.setFillColor(colors.black)
    position_y -= 35

    #Nom des fichiers comparés
    nom_texte_1 = donnees.get("nom1", "Texte collé (sans fichier)")
    nom_texte_2 = donnees.get("nom2", "Texte collé (sans fichier)")

    document_pdf.setFont("Helvetica-Bold", 11)
    document_pdf.drawString(marge, position_y, "Texte 1 : " + nom_texte_1)
    position_y -= 18
    document_pdf.drawString(marge, position_y, "Texte 2 : " + nom_texte_2)
    position_y -= 30

    #Barre des résultats
    document_pdf.setFont("Helvetica-Bold", 12)
    document_pdf.drawString(marge, position_y, "Résultats de l'analyse")
    position_y -= 24

    mesures = [
        ("Mots identiques", donnees["identique"], "#3B82F6"),
        ("Similitude globale", donnees["similitude"], "#4F46E5"),
        ("Différences", donnees["different"], "#EF4444"),
    ]

    largeur_barre = largeur_page - 2 * marge - 90

    for nom_mesure, valeur, couleur in mesures:
        document_pdf.setFont("Helvetica", 10)
        document_pdf.drawString(marge, position_y, nom_mesure)

        x_barre = marge + 115

        # Fond gris de la barre
        document_pdf.setFillColor(colors.HexColor("#F1F5F9"))
        document_pdf.rect(x_barre, position_y - 4, largeur_barre, 14, fill=1, stroke=0)

        # Partie colorée correspondant au pourcentage
        document_pdf.setFillColor(colors.HexColor(couleur))
        document_pdf.rect(x_barre, position_y - 4, largeur_barre * valeur / 100, 14, fill=1, stroke=0)

        # Texte du pourcentage
        document_pdf.setFillColor(colors.black)
        document_pdf.drawString(x_barre + largeur_barre + 10, position_y, f"{valeur:.1f}%")

        position_y -= 28

    position_y -= 8

    #Stat
    document_pdf.setFont("Helvetica-Bold", 12)
    document_pdf.drawString(marge, position_y, "Statistiques")
    position_y -= 22

    document_pdf.setFont("Helvetica", 10)
    document_pdf.drawString(marge, position_y, f"Nombre de mots — Texte 1 : {donnees['mots1']}")
    position_y -= 18
    document_pdf.drawString(marge, position_y, f"Nombre de mots — Texte 2 : {donnees['mots2']}")
    position_y -= 30

    #Légende
    document_pdf.setFont("Helvetica-Bold", 12)
    document_pdf.drawString(marge, position_y, "Légende des couleurs")
    position_y -= 22

    document_pdf.setFont("Helvetica", 10)
    legende = [
        ("Différent (rouge)", "#EF4444"),
        ("Modifié (vert)", "#16A34A"),
    ]

    for texte_legende, couleur in legende:
        document_pdf.setFillColor(colors.HexColor(couleur))
        document_pdf.circle(marge + 5, position_y + 3, 5, fill=1, stroke=0)

        document_pdf.setFillColor(colors.black)
        document_pdf.drawString(marge + 18, position_y, texte_legende)

        position_y -= 18

    document_pdf.showPage()
    document_pdf.save()
    memoire_tampon.seek(0)

    return send_file(
        memoire_tampon,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="rapport_analyse.pdf",
    )




if __name__ == "__main__":
    app.run(debug=True)
