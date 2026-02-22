from fantasybaseball.model import ProjectionSource, ProjectionSourceName


class TestProjectionSource:
    def test_eq_same_source(self):
        a = ProjectionSource(ProjectionSourceName.STEAMER)
        b = ProjectionSource(ProjectionSourceName.STEAMER)
        assert a == b

    def test_eq_different_source(self):
        a = ProjectionSource(ProjectionSourceName.STEAMER)
        b = ProjectionSource(ProjectionSourceName.ZIPS)
        assert a != b

    def test_eq_with_string(self):
        source = ProjectionSource(ProjectionSourceName.STEAMER)
        assert source == "steamer"
        assert source != "zips"

    def test_hash_consistency(self):
        a = ProjectionSource(ProjectionSourceName.STEAMER)
        b = ProjectionSource(ProjectionSourceName.STEAMER)
        assert hash(a) == hash(b)

    def test_usable_as_dict_key(self):
        source = ProjectionSource(ProjectionSourceName.STEAMER)
        d = {source: 42}
        assert d[ProjectionSource(ProjectionSourceName.STEAMER)] == 42

    def test_ros_value(self):
        source = ProjectionSource(ProjectionSourceName.STEAMER, ros=True)
        assert source.value == "steamerr"

    def test_ros_equality(self):
        a = ProjectionSource(ProjectionSourceName.STEAMER, ros=True)
        b = ProjectionSource(ProjectionSourceName.STEAMER, ros=False)
        assert a != b

    def test_string_init(self):
        source = ProjectionSource("steamer")
        assert source.name == ProjectionSourceName.STEAMER
        assert source.value == "steamer"

    def test_the_bat_x_comparison_with_string(self):
        """The bug that was fixed: ProjectionSource compared against string in DataFrame."""
        source = ProjectionSource(ProjectionSourceName.THE_BAT_X)
        assert source == "thebatx"
        assert source == ProjectionSource(ProjectionSourceName.THE_BAT_X)
