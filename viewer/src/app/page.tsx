import Link from "next/link";
import { listProjects } from "@/lib/projects";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Upload,
  AlertTriangle,
  FolderOpen,
  BookOpen,
  BarChart3,
} from "lucide-react";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "success" | "warning"> = {
  new: "secondary",
  discovery: "warning",
  estimation: "warning",
  ready: "success",
  pushed: "success",
};

export const dynamic = "force-dynamic";

export default function HomePage() {
  const projects = listProjects();

  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <FolderOpen className="h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
        <h2 className="text-lg font-semibold mb-2">No projects found</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))] text-center max-w-md">
          Create a project with{" "}
          <code className="px-1.5 py-0.5 rounded bg-[hsl(var(--muted))] text-xs">
            xproject init &lt;name&gt;
          </code>{" "}
          in the terminal to get started.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Projects</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          {projects.length} project{projects.length !== 1 ? "s" : ""} found
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {projects.map((project) => (
          <Link key={project.name} href={`/projects/${project.name}`}>
            <Card className="transition-shadow hover:shadow-md cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{project.name}</CardTitle>
                  <Badge variant={STATUS_VARIANT[project.status] || "secondary"}>
                    {project.status}
                  </Badge>
                </div>
                {project.adoOrg && project.adoProject && (
                  <CardDescription>
                    {project.adoOrg} / {project.adoProject}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 text-sm text-[hsl(var(--muted-foreground))]">
                  <div className="flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5" />
                    <span>{project.filesIngested} files</span>
                  </div>
                  {project.hasOverview && (
                    <div className="flex items-center gap-1.5">
                      <BookOpen className="h-3.5 w-3.5" />
                      <span>Overview</span>
                    </div>
                  )}
                  {project.hasBreakdown && (
                    <div className="flex items-center gap-1.5">
                      <BarChart3 className="h-3.5 w-3.5" />
                      <span>Breakdown</span>
                    </div>
                  )}
                  {project.storiesPushed > 0 && (
                    <div className="flex items-center gap-1.5">
                      <Upload className="h-3.5 w-3.5" />
                      <span>{project.storiesPushed} stories</span>
                    </div>
                  )}
                  {project.changesProcessed > 0 && (
                    <div className="flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>{project.changesProcessed} CRs</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
