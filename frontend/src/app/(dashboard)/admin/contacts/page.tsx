"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import type { ContactRequestItem } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Loader2, Eye, MessageSquare } from "lucide-react";
import { toast } from "sonner";

export default function AdminContactsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<ContactRequestItem | null>(null);
  const [replyText, setReplyText] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "contacts", page],
    queryFn: async () => {
      const res = await adminApi.listContactRequests(page);
      return res;
    },
  });

  const updateStatus = useMutation({
    mutationFn: ({
      id,
      status,
      reply,
    }: {
      id: string;
      status: "resolved" | "open";
      reply?: string;
    }) => adminApi.updateContactRequest(id, { status, reply }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "contacts"] });
      toast.success(res.message || "Updated");
      setSelected(null);
      setReplyText("");
    },
    onError: (e: Error) => {
      // The status may already be saved even if the reply email failed
      queryClient.invalidateQueries({ queryKey: ["admin", "contacts"] });
      toast.error(e.message || "Failed to update");
    },
  });

  const contacts = data?.data?.items || [];

  const statusColors: Record<string, string> = {
    new: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
    in_progress: "bg-yellow-500/15 text-yellow-800 dark:text-yellow-300",
    resolved: "bg-green-500/15 text-green-800 dark:text-green-400",
    closed: "bg-gray-500/15 text-gray-600",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Contact Requests</h1>
        <p className="text-muted-foreground">
          View and respond to user contact submissions
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : contacts.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent>
            <Mail className="mx-auto h-12 w-12 text-muted-foreground" />
            <CardTitle className="mt-4">No Contact Requests</CardTitle>
            <CardDescription className="mt-2">
              Submissions from the contact form will appear here
            </CardDescription>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contacts.map((contact: ContactRequestItem) => (
                <TableRow key={contact.id}>
                  <TableCell className="font-medium">{contact.name}</TableCell>
                  <TableCell>{contact.email}</TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    {contact.subject}
                  </TableCell>
                  <TableCell>
                    <Badge className={statusColors[contact.is_resolved ? "resolved" : "new"] || ""}>
                      {contact.is_resolved ? "resolved" : "new"}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(contact.created_at)}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setSelected(contact)}
                      aria-label="View request"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">Page {page}</span>
        <Button
          variant="outline"
          size="sm"
          disabled={contacts.length < 20}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </Button>
      </div>

      {/* Detail Dialog */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Contact Request</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Name</p>
                  <p className="font-medium">{selected.name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Email</p>
                  <p className="font-medium">{selected.email}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Subject</p>
                  <p className="font-medium">{selected.subject}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Date</p>
                  <p className="font-medium">
                    {formatDate(selected.created_at)}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Message</p>
                <p className="mt-1 whitespace-pre-wrap rounded-lg border p-4 text-sm">
                  {selected.message}
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Status</label>
                <Badge
                  className={
                    selected.is_resolved
                      ? statusColors.resolved
                      : statusColors.new
                  }
                >
                  {selected.is_resolved ? "Resolved" : "Pending"}
                </Badge>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Reply</label>
                <Textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Type a reply to send via email..."
                  rows={4}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelected(null)}>
              Close
            </Button>
            {selected && !replyText && (
              <Button
                variant="secondary"
                onClick={() =>
                  updateStatus.mutate({
                    id: selected.id,
                    status: selected.is_resolved ? "open" : "resolved",
                  })
                }
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {selected.is_resolved ? "Reopen" : "Mark Resolved"}
              </Button>
            )}
            {selected && replyText && (
              <Button
                onClick={() =>
                  updateStatus.mutate({
                    id: selected.id,
                    status: "resolved",
                    reply: replyText,
                  })
                }
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <MessageSquare className="mr-2 h-4 w-4" />
                )}
                Send Reply &amp; Resolve
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
