/**
 * Types JSDoc des payloads API communauté (miroir de site/api/schemas/).
 */

/**
 * @typedef {Object} InscriptionPayload
 * @property {string} email
 * @property {string} pseudo
 * @property {string} mot_de_passe
 * @property {boolean} age_18_plus
 * @property {boolean} cgu_acceptees
 */

/**
 * @typedef {Object} ConnexionPayload
 * @property {string} [identifiant]
 * @property {string} [email]
 * @property {string} mot_de_passe
 */

/**
 * @typedef {Object} CommentaireMatchPayload
 * @property {string} championnat
 * @property {string} saison
 * @property {string} domicile
 * @property {string} exterieur
 * @property {string} contenu
 * @property {number} [commentaire_parent_id]
 */

/**
 * @typedef {Object} PronosticPayload
 * @property {string} championnat
 * @property {string} saison
 * @property {string} domicile
 * @property {string} exterieur
 * @property {'score'|'1x2'} type_pronostic
 * @property {number} [buts_domicile]
 * @property {number} [buts_exterieur]
 * @property {'1'|'N'|'2'} [resultat_1x2]
 */

/**
 * @typedef {Object} ProfilMajPayload
 * @property {string} [bio]
 * @property {string} [equipe_favorite]
 * @property {string} [avatar_id]
 * @property {string} [pseudo]
 */

/**
 * @typedef {Object} LigueCreerPayload
 * @property {string} nom
 */

/**
 * @typedef {Object} ReactionPayload
 * @property {'pouce'|'coeur'|'ballon'|'feu'|'rire'|'applaudir'} [type_reaction]
 */

export {};
