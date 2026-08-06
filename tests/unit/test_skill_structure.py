"""Tests for SKILL.md structure and content validation."""

import re
from pathlib import Path

import pytest
import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"
ALL_SKILL_MD_FILES = sorted(SKILLS_ROOT.glob("*/SKILL.md"))


class TestAllSkillsFrontmatter:
    """Every skills/*/SKILL.md must have frontmatter valid per the Agent Skills spec."""

    @pytest.fixture(params=ALL_SKILL_MD_FILES, ids=lambda p: p.parent.name)
    def skill_file(self, request):
        """Each SKILL.md file in the skills directory."""
        return request.param

    @pytest.fixture
    def frontmatter(self, skill_file):
        """Parse YAML frontmatter from the skill file."""
        content = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            pytest.fail(f"{skill_file} missing YAML frontmatter")
        return yaml.safe_load(match.group(1))

    def test_skills_discovered(self):
        """The glob must find the skills (guards against a moved skills/ dir)."""
        assert len(ALL_SKILL_MD_FILES) >= 1

    def test_name_matches_directory(self, skill_file, frontmatter):
        """Frontmatter name must match the skill's directory name."""
        assert frontmatter.get("name") == skill_file.parent.name

    def test_description_within_spec_limits(self, frontmatter):
        """Description must be meaningful and within the spec's 1024-char limit."""
        description = frontmatter.get("description") or ""
        assert 20 < len(description) <= 1024


class TestOrchestratorSkillMd:
    """Test that orchestrator SKILL.md (skills/rhdh/SKILL.md) has required structure."""

    @pytest.fixture
    def skill_md(self, skills_dir):
        """Load orchestrator SKILL.md content."""
        skill_path = skills_dir / "SKILL.md"
        return skill_path.read_text(encoding="utf-8")

    @pytest.fixture
    def skill_frontmatter(self, skill_md):
        """Parse YAML frontmatter from SKILL.md."""
        match = re.match(r"^---\n(.*?)\n---", skill_md, re.DOTALL)
        if not match:
            pytest.fail("SKILL.md missing YAML frontmatter")
        return yaml.safe_load(match.group(1))

    def test_frontmatter_has_name(self, skill_frontmatter):
        """SKILL.md must have a name field."""
        assert "name" in skill_frontmatter
        assert skill_frontmatter["name"] == "rhdh"

    def test_frontmatter_has_description(self, skill_frontmatter):
        """SKILL.md must have a description field."""
        assert "description" in skill_frontmatter
        assert len(skill_frontmatter["description"]) > 20

    def test_has_cli_setup_section(self, skill_md):
        """SKILL.md must have <cli_setup> section."""
        assert "<cli_setup>" in skill_md
        assert "</cli_setup>" in skill_md

    def test_has_essential_principles(self, skill_md):
        """SKILL.md must have <essential_principles> section."""
        assert "<essential_principles>" in skill_md
        assert "</essential_principles>" in skill_md

    def test_has_intake_section(self, skill_md):
        """SKILL.md must have <intake> section with menu."""
        assert "<intake>" in skill_md
        assert "</intake>" in skill_md
        # Should have numbered options
        assert re.search(r"1\.\s+\*\*", skill_md)

    def test_has_routing_section(self, skill_md):
        """SKILL.md must have <routing> section with table."""
        assert "<routing>" in skill_md
        assert "</routing>" in skill_md
        # Should have markdown table
        assert "| Response |" in skill_md or "| Intent |" in skill_md or "| Condition |" in skill_md

    def test_has_cli_commands_section(self, skill_md):
        """SKILL.md must have <cli_commands> section."""
        assert "<cli_commands>" in skill_md
        assert "</cli_commands>" in skill_md
        assert "$RHDH" in skill_md

    def test_references_cli_variable(self, skill_md):
        """SKILL.md should use $RHDH variable consistently."""
        # Count references to the variable
        matches = re.findall(r"\$RHDH", skill_md)
        assert len(matches) >= 3, "Should reference $RHDH multiple times"

    def test_routes_to_overlay_skill(self, skill_md):
        """Orchestrator should route to overlay skill."""
        assert "overlay" in skill_md.lower()


class TestOverlaySkillMd:
    """Test that overlay SKILL.md (skills/overlay/SKILL.md) has required structure."""

    @pytest.fixture
    def skill_md(self, overlay_skill_dir):
        """Load overlay SKILL.md content."""
        skill_path = overlay_skill_dir / "SKILL.md"
        return skill_path.read_text(encoding="utf-8")

    @pytest.fixture
    def skill_frontmatter(self, skill_md):
        """Parse YAML frontmatter from SKILL.md."""
        match = re.match(r"^---\n(.*?)\n---", skill_md, re.DOTALL)
        if not match:
            pytest.fail("SKILL.md missing YAML frontmatter")
        return yaml.safe_load(match.group(1))

    def test_frontmatter_has_name(self, skill_frontmatter):
        """SKILL.md must have a name field."""
        assert "name" in skill_frontmatter
        assert skill_frontmatter["name"] == "overlay"

    def test_frontmatter_has_description(self, skill_frontmatter):
        """SKILL.md must have a description field."""
        assert "description" in skill_frontmatter
        assert len(skill_frontmatter["description"]) > 20

    def test_has_essential_principles(self, skill_md):
        """SKILL.md must have <essential_principles> section."""
        assert "<essential_principles>" in skill_md
        assert "</essential_principles>" in skill_md

    def test_has_intake_section(self, skill_md):
        """SKILL.md must have <intake> section with menu."""
        assert "<intake>" in skill_md
        assert "</intake>" in skill_md
        # Should have numbered options
        assert re.search(r"1\.\s+\*\*", skill_md)

    def test_has_routing_section(self, skill_md):
        """SKILL.md must have <routing> section with table."""
        assert "<routing>" in skill_md
        assert "</routing>" in skill_md
        # Should have markdown table
        assert "| Response |" in skill_md

    def test_has_success_criteria(self, skill_md):
        """SKILL.md must have <success_criteria> section."""
        assert "<success_criteria>" in skill_md
        assert "</success_criteria>" in skill_md

    def test_references_workflows(self, skill_md):
        """Overlay skill should reference its workflows."""
        assert "workflows/" in skill_md

    def test_no_markdown_headings_in_xml_body(self, skill_md):
        """XML sections should not use markdown headings (# or ##) outside code blocks."""
        # Extract content between xml tags (excluding sections that commonly have code)
        excluded = r"quick_start|cli_commands|inline_status_check|context_scan"
        xml_sections = re.findall(rf"<(?!{excluded})(\w+)>(.*?)</\1>", skill_md, re.DOTALL)

        for section_name, content in xml_sections:
            # Track if we're inside a code block
            in_code_block = False
            lines = content.split("\n")

            for line in lines:
                # Toggle code block state
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue

                # Skip lines in code blocks and table lines
                if in_code_block or line.strip().startswith("|"):
                    continue

                # Check for markdown headings at start of line
                if re.match(r"^#{1,3}\s", line.strip()):
                    # Allow in sections that commonly use subheadings for organization
                    allowed_sections = (
                        "intake",
                        "routing",
                        "workflows_index",
                        "success_criteria",
                        "tracking_system",
                    )
                    if section_name in allowed_sections:
                        continue
                    pytest.fail(f"Found markdown heading in <{section_name}>: {line.strip()}")


class TestSkillMakerSkillMd:
    """Test that skill-maker SKILL.md keeps router intake pause instructions."""

    @pytest.fixture
    def skill_md(self, skill_maker_dir):
        """Load skill-maker SKILL.md content."""
        skill_path = skill_maker_dir / "SKILL.md"
        return skill_path.read_text(encoding="utf-8")

    def test_intake_waits_for_user_response(self, skill_md):
        """The intake section must tell the agent to wait before routing."""
        match = re.search(r"<intake>(.*?)</intake>", skill_md, re.DOTALL)
        assert match, "SKILL.md missing <intake> section"
        assert "**Wait for response before proceeding.**" in match.group(1)


class TestWorkflowStructure:
    """Test that workflow files have required structure."""

    @pytest.fixture
    def workflow_files(self, overlay_skill_dir):
        """Get all workflow files from overlay skill."""
        workflows_dir = overlay_skill_dir / "workflows"
        return list(workflows_dir.glob("*.md"))

    def test_workflows_exist(self, workflow_files):
        """At least one workflow should exist."""
        assert len(workflow_files) >= 1

    def test_workflow_has_required_reading(self, workflow_files):
        """Each workflow should have <required_reading> section."""
        for workflow in workflow_files:
            content = workflow.read_text(encoding="utf-8")
            assert "<required_reading>" in content or "<prerequisites>" in content, (
                f"{workflow.name} missing required_reading or prerequisites"
            )

    def test_workflow_has_process(self, workflow_files):
        """Each workflow should have <process> section."""
        for workflow in workflow_files:
            content = workflow.read_text(encoding="utf-8")
            assert "<process>" in content, f"{workflow.name} missing <process> section"
            assert "</process>" in content, f"{workflow.name} missing </process> closing tag"

    def test_workflow_has_success_criteria(self, workflow_files):
        """Each workflow should have <success_criteria> section."""
        for workflow in workflow_files:
            content = workflow.read_text(encoding="utf-8")
            assert "<success_criteria>" in content, (
                f"{workflow.name} missing <success_criteria> section"
            )


class TestRhdhReposReference:
    """Test that rhdh-repos.md reference file exists and has required content."""

    @pytest.fixture
    def rhdh_repos(self, skills_dir):
        """Load rhdh-repos.md content."""
        path = skills_dir / "references" / "rhdh-repos.md"
        assert path.exists(), "rhdh-repos.md must exist in skills/rhdh/references/"
        return path.read_text(encoding="utf-8")

    def test_rhdh_repos_exists(self, skills_dir):
        """rhdh-repos.md must exist."""
        assert (skills_dir / "references" / "rhdh-repos.md").exists()

    def test_has_key_repos(self, rhdh_repos):
        """Must document the core RHDH repositories."""
        for repo in ["rhdh", "rhdh-cli", "rhdh-operator", "rhdh-plugins"]:
            assert repo in rhdh_repos, f"Missing repo: {repo}"

    def test_has_ecosystem_relationships(self, rhdh_repos):
        """Must contain ecosystem relationships section."""
        assert "Ecosystem Relationships" in rhdh_repos

    def test_no_hardcoded_user_paths(self, rhdh_repos):
        """Must not contain hardcoded user-specific paths."""
        assert "/Users/" not in rhdh_repos
        assert "/home/" not in rhdh_repos

    def test_no_yaml_frontmatter(self, rhdh_repos):
        """Reference file should not have YAML frontmatter."""
        assert not rhdh_repos.startswith("---")

    def test_has_upstream_urls(self, rhdh_repos):
        """Must include upstream GitHub URLs."""
        assert "github.com/redhat-developer/" in rhdh_repos


class TestReferenceStructure:
    """Test that reference files have required structure."""

    @pytest.fixture
    def reference_files(self, skills_dir, overlay_skill_dir):
        """Get all reference files from both skills."""
        refs = []
        refs.extend((skills_dir / "references").glob("*.md"))
        refs.extend((overlay_skill_dir / "references").glob("*.md"))
        return refs

    def test_references_exist(self, reference_files):
        """At least one reference should exist."""
        assert len(reference_files) >= 1

    def test_reference_has_xml_sections(self, reference_files):
        """Reference files should use XML tags for structure (optional for cheatsheets)."""
        # Some reference files are practical cheatsheets without XML structure
        xml_optional = {
            "jira-reference.md",
            "jira-structure.md",
            "github-tips.md",
            "private-data.md",
            "rhdh-repos.md",
            "versions.md",
        }

        for ref in reference_files:
            if ref.name in xml_optional:
                continue
            content = ref.read_text(encoding="utf-8")
            # Should have at least one XML tag
            has_xml = bool(re.search(r"<\w+>", content))
            assert has_xml, f"{ref.name} should use XML tags for structure"


class TestTemplateStructure:
    """Test that template files exist and are valid."""

    @pytest.fixture
    def template_files(self, overlay_skill_dir):
        """Get all template files from overlay skill."""
        templates_dir = overlay_skill_dir / "templates"
        return list(templates_dir.glob("*.md"))

    def test_templates_exist(self, template_files):
        """At least one template should exist."""
        assert len(template_files) >= 1

    def test_template_has_code_blocks(self, template_files):
        """Templates should contain code block examples."""
        for template in template_files:
            content = template.read_text(encoding="utf-8")
            assert "```" in content, f"{template.name} should have code block examples"
