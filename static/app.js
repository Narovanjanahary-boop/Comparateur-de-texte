let last = null;
let names = ["", ""];


const $ = id => document.getElementById(id);


function text(n) {
    return $("text" + n).innerText;
}


function setStatus(s) {
    $("status").textContent = s;
}


// IMPORTATION DES FICHIERS

async function loadFile(n) {
    const f = $("file" + n).files[0];

    if (!f) {
        return;
    }

    const fd = new FormData();
    fd.append("file", f);

    const r = await fetch("/api/fichier", {
        method: "POST",
        body: fd
    });

    const d = await r.json();

    if (!r.ok) {
        return alert(d.error || "Erreur d'importation");
    }

    $("text" + n).innerText = d.text;
    $("name" + n).textContent = d.filename;
    names[n] = d.filename;

    setStatus("Fichier importé : " + d.filename);

    auto();
}


// ANALYSE AUTO

let timer;


function auto() {
    clearTimeout(timer);

    timer = setTimeout(() => {
        if (text(1).trim() && text(2).trim()) {
            analyse();
        }
    }, 700);
}


[1, 2].forEach(n => {
    $("text" + n).addEventListener("input", auto);
});

// ANALYSE DES TEXTES

async function analyse() {

    if (!text(1).trim() || !text(2).trim()) {
        return alert(
            "Collez ou importez du texte dans les deux cases avant de lancer l'analyse."
        );
    }

    const fd = new FormData();

    fd.append("texte1", text(1));
    fd.append("texte2", text(2));

    const r = await fetch("/api/analyse", {
        method: "POST",
        body: fd
    });

    const d = await r.json();

    if (!r.ok) {
        return alert(d.error);
    }

    last = d;

    renderClasses(1, d.classes1);
    renderClasses(2, d.classes2);
    renderResults(d.stats);

    setStatus(
        `Analyse terminée — ${d.stats.pourcentage_similitude.toFixed(1)}% de similitude globale entre les deux textes.`
    );
}


// PROTECTION DU HTML

function escapeHtml(s) {
    return s.replace(
        /[&<>"]/g,
        c => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;"
        }[c])
    );
}


// Affichage des différences

function renderClasses(n, classes) {

    const words = text(n).split(/(\s+)/);

    let idx = 0;
    let html = "";

    for (const w of words) {

        if (/^\s+$/.test(w)) {
            html += w;
            continue;
        }

        const cls = classes[idx++] || "";

        html += cls
            ? `<span class="${cls}">${escapeHtml(w)}</span>`
            : escapeHtml(w);
    }

    $("text" + n).innerHTML = html;

    placeCaretEnd($("text" + n));
}


function placeCaretEnd(el) {

    el.focus();

    let r = document.createRange();

    r.selectNodeContents(el);
    r.collapse(false);

    let s = getSelection();

    s.removeAllRanges();
    s.addRange(r);
}



// Affichage des résultats

function renderResults(s) {

    const m = [
        [
            "Mots identiques",
            s.pourcentage_identique,
            "#3B82F6"
        ],
        [
            "Similitude globale",
            s.pourcentage_similitude,
            "#4F46E5"
        ],
        [
            "Différences",
            s.pourcentage_different,
            "#EF4444"
        ]
    ];


    $("resultsBody").className = "results-body";


    $("resultsBody").innerHTML = `
        <div class="metrics">

            <div class="donuts">

                ${m.map(x => `
                    <div class="metric">

                        <div
                            class="donut"
                            style="--v:${x[1]};--c:${x[2]}"
                        >
                            <span>
                                ${x[1].toFixed(0)}%
                            </span>
                        </div>

                        <div>
                            ${x[0]}
                        </div>

                    </div>
                `).join("")}

            </div>


            <div class="bars">

                <b>
                    Résultat visuel (graphique) de l'analyse
                </b>


                ${m.map(x => `
                    <div class="barline">

                        <span>
                            ${x[0]}
                        </span>

                        <div class="bar">

                            <div
                                class="fill"
                                style="width:${x[1]}%;background:${x[2]}"
                            ></div>

                        </div>

                        <span>
                            ${x[1].toFixed(1)}%
                        </span>

                    </div>
                `).join("")}


                <small>
                    Texte 1 : ${s.nombre_mots_1} mots |
                    Texte 2 : ${s.nombre_mots_2} mots |
                    ${s.pourcentage_identique.toFixed(1)}% de mots identiques |
                    ${s.pourcentage_similitude.toFixed(1)}% de similitude |
                    ${s.pourcentage_different.toFixed(1)}% de différence
                </small>

            </div>

        </div>
    `;
}



// RECHERCHER MOT

async function rechercher() {

    const mot = prompt("Mot ou expression à rechercher :");

    if (!mot) {
        return;
    }


    document
        .querySelectorAll(".recherche")
        .forEach(e => e.classList.remove("recherche"));


    const r = await fetch("/api/recherche", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            mot,
            texts: [
                text(1),
                text(2)
            ]
        })
    });


    const d = await r.json();


    [1, 2].forEach((n, k) => {

        let root = $("text" + n);
        let raw = root.innerText;
        let occ = d.occurrences[k];

        let html = "";
        let p = 0;


        occ.forEach(([a, b]) => {

            html +=
                escapeHtml(raw.slice(p, a)) +
                `<mark class="recherche">${escapeHtml(raw.slice(a, b))}</mark>`;

            p = b;
        });


        html += escapeHtml(raw.slice(p));

        root.innerHTML = html;
    });


    setStatus(
        d.total
            ? `${d.total} occurrence(s) de « ${mot} » mise(s) en évidence.`
            : `Aucune occurrence de « ${mot} » trouvée.`
    );
}


// RECOMMENCER ANALYSE

function recommencer() {

    if (!text(1).trim() || !text(2).trim()) {
        return alert(
            "Collez ou importez du texte dans les deux cases avant de recommencer l'analyse."
        );
    }

    analyse();
}



// RESTAURER APPLI

function restaurer() {

    if (
        !confirm(
            "Retirer le contenu des deux cases et effacer les résultats d'analyse ?"
        )
    ) {
        return;
    }


    [1, 2].forEach(n => {

        $("text" + n).innerHTML = "";

        $("name" + n).textContent =
            `Aucun fichier — Texte ${n} (collez votre texte ou importez un fichier)`;
    });


    last = null;


    $("resultsBody").className =
        "results-body empty";


    $("resultsBody").textContent =
        "Collez du texte ou importez deux fichiers dans les deux cases, puis lancez l'analyse (▶) pour afficher les résultats ici.";


    setStatus(
        "Application réinitialisée. Collez du texte ou importez deux fichiers pour recommencer."
    );
}



// INFORMATION DU FICHIER

function fileInfo(n) {

    let t = text(n);


    alert(
        t
            ? `Origine : texte collé / importé

Nombre de mots : ${
    t.trim()
        ? t.trim().split(/\s+/).length
        : 0
}

Nombre de lignes : ${
    t.split("\n").length
}

Nombre de caractères : ${
    t.length
}`
            : "Aucun texte n'a encore été collé ou importé dans cette case."
    );
}



// CREER PDF

async function exportPDF() {

    if (!last) {
        return alert(
            "Lancez d'abord une analyse (importez les deux fichiers)."
        );
    }


    const s = last.stats;


    const r = await fetch("/api/pdf", {
        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            identique: s.pourcentage_identique,
            similitude: s.pourcentage_similitude,
            different: s.pourcentage_different,
            mots1: s.nombre_mots_1,
            mots2: s.nombre_mots_2,
            nom1: names[1],
            nom2: names[2]
        })
    });


    if (!r.ok) {

        let d = await r.json();

        return alert(d.error);
    }


    const b = await r.blob();

    const u = URL.createObjectURL(b);

    const a = document.createElement("a");

    a.href = u;
    a.download = "rapport_analyse.pdf";

    a.click();

    URL.revokeObjectURL(u);


    setStatus("Rapport PDF exporté.");
}



// MES INFOS

function about() {

    openModal(`
        <h2>ℹ️ À propos</h2>
        ${escapeHtml(
            `Analyseur de Textes Comparatif — v1.0

${TEXTE_INFO}`
        )}
    `);
}


const TEXTE_INFO = `Application de comparaison et d'analyse de deux fichiers texte (TXT, PDF, DOCX, RTF...) avec résultats visuels et graphiques.

Auteur : NAROVANJANAHARY Solofoniaina Ferdinand
Etudiant : 1ère année de Licence Informatique à l' EMIT Fianarantsoa(DA2I)
E-mail : rovaferdinand844@gmail.com
Whatsapp : +261383167780

Portfolio : ${"https://narovanjanahary-boop.github.io/portfolio/"}
Facebook : ${"https://web.facebook.com/profile.php?id=61555340056112"}
GitHub : ${"https://github.com/Narovanjanahary-boop"}`;



// FENETRE MODALE

function openModal(c) {

    $("modalContent").innerHTML = c;

    $("modal").hidden = false;
}


function closeModal() {

    $("modal").hidden = true;
}