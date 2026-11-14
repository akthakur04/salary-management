"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { ApiError } from "@/lib/api";
import { EMPLOYMENT_TYPE_LABELS, formatDate } from "@/lib/format";
import { useTerminate, useUpdateEmployee } from "@/lib/queries";
import type { EmployeeProfile, EmploymentType } from "@/lib/types";

function message(error: unknown): string {
  return error instanceof ApiError ? error.message : "That didn't save. Try again in a moment.";
}

/** Non-pay details, plus recording a last day. Pay changes go through Revise compensation. */
export function EditDetailsDialog({ profile }: { profile: EmployeeProfile }) {
  const [open, setOpen] = useState(false);
  const update = useUpdateEmployee(profile.id);
  const terminate = useTerminate(profile.id);
  const [name, setName] = useState(profile.name);
  const [email, setEmail] = useState(profile.email);
  const [type, setType] = useState<EmploymentType>(profile.employment_type);
  const [fte, setFte] = useState(profile.fte);
  const [status, setStatus] = useState(profile.status === "on_leave" ? "on_leave" : "active");
  const [lastDay, setLastDay] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await update.mutateAsync({
        name,
        email,
        employment_type: type,
        fte: type === "part_time" ? fte : "1",
        status,
      });
      toast.success("Details saved.");
      setOpen(false);
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function recordLastDay() {
    setError(null);
    try {
      await terminate.mutateAsync(lastDay);
      toast.success(`Last day recorded: ${formatDate(lastDay)}.`);
      setOpen(false);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="h-10 bg-card px-3.5">
          Edit details
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit details</DialogTitle>
          <DialogDescription>
            Name, contact and employment. Pay changes are recorded with Revise compensation.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <p role="alert" className="rounded-lg bg-rose-tint px-3 py-2 text-[13px] text-rose-text">
            {error}
          </p>
        ) : null}

        <form id="edit-details" onSubmit={save} className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="edit-name">Name</Label>
            <Input id="edit-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="edit-email">Work email</Label>
            <Input
              id="edit-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-type">Employment type</Label>
            <Select value={type} onValueChange={(value) => setType(value as EmploymentType)}>
              <SelectTrigger id="edit-type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(EMPLOYMENT_TYPE_LABELS) as EmploymentType[]).map((option) => (
                  <SelectItem key={option} value={option}>
                    {EMPLOYMENT_TYPE_LABELS[option]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-fte">FTE</Label>
            <Input
              id="edit-fte"
              inputMode="decimal"
              value={type === "part_time" ? fte : "1.00"}
              disabled={type !== "part_time"}
              onChange={(e) => setFte(e.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="edit-status">Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger id="edit-status" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="on_leave">On leave</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </form>

        <DialogFooter>
          <Button type="submit" form="edit-details" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save details"}
          </Button>
        </DialogFooter>

        {profile.termination_date === null ? (
          <>
            <Separator />
            <div className="flex flex-col gap-3">
              <div>
                <h3 className="text-sm font-semibold">End employment</h3>
                <p className="text-[13px] text-muted-foreground">
                  Record the last day worked. It can be in the future. The record and salary
                  history are kept.
                </p>
              </div>
              <div className="flex flex-wrap items-end gap-2">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="last-day">Last day</Label>
                  <Input
                    id="last-day"
                    type="date"
                    value={lastDay}
                    onChange={(e) => setLastDay(e.target.value)}
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  className="border-rose text-rose-text hover:bg-rose-tint"
                  disabled={!lastDay || terminate.isPending}
                  onClick={recordLastDay}
                >
                  Record last day
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
