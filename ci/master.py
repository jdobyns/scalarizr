
from buildbot.schedulers.basic import AnyBranchScheduler
from buildbot.changes.filter import ChangeFilter
from buildbot.process.factory import BuildFactory
from buildscripts import steps as buildsteps


project = __opts__['project']


c['schedulers'].append(AnyBranchScheduler(
	name=project,
	change_filter=ChangeFilter(project=project, category='default'),
	builderNames=['{0} source'.format(project)]
))


c["schedulers"].append(Triggerable(
	name="{0} packaging".format(project),
	builderNames=["deb_packaging_1004"]
))


c['builders'].append(dict(
	name='{0} source'.format(project),
	slavenames=['ubuntu1004'],
	factory=BuildFactory(steps=
		buildsteps.svn(__opts__) +
		buildsteps.bump_version(__opts__) +
		buildsteps.source_dist(__opts__)# +
		#buildsteps.trigger_packaging(__opts__)
	)
))

