from alembic.testing.fixtures import TestBase
from alembic.testing import eq_
from alembic.revision import RevisionMap, Revision


class DownIterateTest(TestBase):
    def _assert_iteration(self, upper, lower, assertion):
        eq_(
            [rev.revision for rev in
             self.map._iterate_revisions(upper, lower)],
            assertion
        )


class DiamondTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('c', ('b1', 'b2')),
                Revision('d', ('c',)),
            ]
        )

    def test_iterate_simple_diamond(self):
        self._assert_iteration(
            "d", "a",
            ["d", "c", "b1", "b2", "a"]
        )


class MultipleBranchTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('d1cb1', ('cb1',)),
                Revision('d2cb1', ('cb1',)),
                Revision('d1cb2', ('cb2',)),
                Revision('d2cb2', ('cb2',)),
                Revision('d3cb2', ('cb2',)),
                Revision('d1d2cb2', ('d1cb2', 'd2cb2'))
            ]
        )

    def test_iterate_from_merge_point(self):
        self._assert_iteration(
            "d1d2cb2", "a",
            ['d1d2cb2', 'd1cb2', 'd2cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_multiple_heads(self):
        self._assert_iteration(
            ["d2cb2", "d3cb2"], "a",
            ['d2cb2', 'd3cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_single_branch(self):
        self._assert_iteration(
            "d3cb2", "a",
            ['d3cb2', 'cb2', 'b2', 'a']
        )


class BranchTravellingTest(DownIterateTest):
    """test the order of revs when going along multiple branches.

    We want depth-first along branches, but then we want to
    terminate all branches at their branch point before continuing
    to the nodes preceding that branch.

    """

    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('a1', ()),
                Revision('a2', ('a1',)),
                Revision('a3', ('a2',)),
                Revision('b1', ('a3',)),
                Revision('b2', ('a3',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('db1', ('cb1',)),
                Revision('db2', ('cb2',)),

                Revision('e1b1', ('db1',)),
                Revision('fe1b1', ('e1b1',)),

                Revision('e2b1', ('db1',)),
                Revision('e2b2', ('db2',)),
                Revision("merge", ('e2b1', 'e2b2'))
            ]
        )

    def test_two_branches_to_root(self):

        # here we want 'a3' as a "stop" branch point, but *not*
        # 'db1', as we don't have multiple traversals on db1
        self._assert_iteration(
            "merge", "a1",
            ['merge',
                'e2b1', 'db1', 'cb1', 'b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'a3',  # both terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )

    def test_two_branches_end_in_branch(self):
        self._assert_iteration(
            "merge", "b1",
            # 'b1' is local to 'e2b1'
            # branch so that is all we get
            ['merge', 'e2b1', 'db1', 'cb1', 'b1',

        ]  # noqa
        )

    def test_two_branches_end_behind_branch(self):
        self._assert_iteration(
            "merge", "a2",
            ['merge',
                'e2b1', 'db1', 'cb1', 'b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'a3',  # both terminate at a3
                'a2'
            ]  # noqa
        )

    def test_three_branches_to_root(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"], "a1",
            ['merge',
                'e2b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'fe1b1', 'e1b1',  # fe1b1 branch
                'db1',  # fe1b1 and e2b1 branches terminate at db1
                'cb1', 'b1',  # e2b1 branch continued....might be nicer
                              # if this was before the e2b2 branch...
                'a3',  # e2b1 and e2b2 branches terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )

    def test_three_branches_end_in_single_branch(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"], "e1b1",
            ['merge',
                'fe1b1', 'e1b1',  # fe1b1 branch
            ]  # noqa
        )

    def test_three_branches_end_multiple_bases(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"], ["cb1", "cb2"],
            [
                'merge',
                'e2b1',
                'e2b2', 'db2', 'cb2',
                'fe1b1', 'e1b1',
                'db1',
                'cb1'
            ]
        )


class MultipleBaseTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('base1', ()),
                Revision('base2', ()),
                Revision('base3', ()),

                Revision('a1a', ('base1',)),
                Revision('a1b', ('base1',)),
                Revision('a2', ('base2',)),
                Revision('a3', ('base3',)),

                Revision('b1a', ('a1a',)),
                Revision('b1b', ('a1b',)),
                Revision('b2', ('a2',)),
                Revision('b3', ('a3',)),

                Revision('c2', ('b2',)),
                Revision('d2', ('c2',)),

                Revision('mergeb3d2', ('b3', 'd2'))
            ]
        )

    def test_head_to_base(self):
        self._assert_iteration(
            "head", "base",
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2', 'c2', 'b2', 'a2', 'base2',
                'base1'
            ]
        )