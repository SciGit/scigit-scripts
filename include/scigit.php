<?

/* Some common code between web and backend. */

define('SCIGIT_DIR', '/var/scigit');
define('SCIGIT_REPO_DIR', '/var/scigit/repos');
define('SCIGIT_REPO_LIMIT', 16 * 1024 * 1024);

function scigit_db_connect() {
	$link = mysql_connect('localhost', 'scigit', 'scigit');
	if (!$link || !mysql_select_db('scigit')) {
		echo 'Could not connect to database.';
		exit(1);
	}
	return $link;
}
