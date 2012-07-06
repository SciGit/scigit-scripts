#!/usr/bin/php
<?

/* Temporary hack. We'll have to have a daemon to do this later. */

require_once '/var/scigit/include/scigit.php';

scigit_db_connect();

chdir(SCIGIT_DIR);
$base = file_get_contents('gitolite-admin/conf/gitolite.conf.base');

// Update the repo/permission config
$f = fopen('gitolite-admin/conf/gitolite.conf', 'w');
fputs($f, $base);
fprintf($f, "\n");

$user_pub_keys = array();
$q = mysql_query('SELECT * FROM user_pub_keys') or die(mysql_error());
while ($r = mysql_fetch_assoc($q)) {
	$user = $r['user_id'];
	if (!isset($user_pub_keys[$user])) $user_pub_keys[$user] = array();
	$user_pub_keys[$user][] = $r;
}

foreach ($user_pub_keys as $user => $keys) {
	$keynames = array();
	foreach ($keys as $key) {
		$keynames[] = 'u' . $user . '.' . $key['id'];
	}
	fprintf($f, "@u%d = %s\n", $user, implode(' ', $keynames));
}
fprintf($f, "\n");

$proj_users = array();
$q = mysql_query('SELECT * FROM projects LEFT JOIN proj_permissions '.
	'ON projects.id = proj_permissions.proj_id') or die(mysql_error());
while ($r = mysql_fetch_assoc($q)) {
	$proj = $r['proj_id'];
	if (!isset($proj_users[$proj])) $proj_users[$proj] = array();
	$proj_users[$proj][] = $r;
}

foreach ($proj_users as $proj => $users) {
	fprintf($f, "repo r%d\n", $proj);
	fprintf($f, "  config scigit.repo.id = %d\n", $proj);
	fprintf($f, "  config scigit.repo.limit = %d\n", SCIGIT_REPO_LIMIT);
	fprintf($f, "  config core.fileMode = false\n");
	fprintf($f, "  R = git\n");
	foreach ($users as $user) {
		$perm = 'R' . ($user['can_write'] ? 'W' : '');
		fprintf($f, "  %s = @u%s\n", $perm, $user['user_id']);
	}
}
fclose($f);

// Get new public keys.
exec('rm gitolite-admin/keydir/u*');
foreach ($user_pub_keys as $user => $keys) {
	foreach ($keys as $key) {
		$name = 'u' . $user . '.' . $key['id'] . '.pub';
		$k = $key['key_type'] . ' ' . $key['public_key'];
		file_put_contents('gitolite-admin/keydir/'.$name, $k);
	}
}

// Push
chdir('gitolite-admin');
exec('git add keydir/u*');
exec('git commit -a -m "update-repos.php"');
exec('git push', $out, $ret);
exit($ret);
