import React, { useState, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

const ConfirmDialog = ({ open, onOpenChange, title, description, onConfirm, confirmLabel = 'Delete', variant = 'destructive' }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="bg-[#0a0a0a] border-white/10 max-w-md">
      <DialogHeader>
        <DialogTitle className="text-white">{title}</DialogTitle>
        <DialogDescription className="text-slate-400">{description}</DialogDescription>
      </DialogHeader>
      <DialogFooter className="gap-2 sm:gap-0">
        <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant={variant} onClick={() => { onConfirm(); onOpenChange(false); }}>{confirmLabel}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

function useConfirmDialog() {
  const [state, setState] = useState({ open: false, title: '', description: '', onConfirm: () => {}, confirmLabel: 'Delete', variant: 'destructive' });

  const confirm = useCallback(({ title, description, onConfirm, confirmLabel = 'Delete', variant = 'destructive' }) => {
    setState({ open: true, title, description, onConfirm, confirmLabel, variant });
  }, []);

  const dialogProps = {
    ...state,
    onOpenChange: (open) => setState((s) => ({ ...s, open })),
  };

  return { confirm, dialogProps, ConfirmDialog };
}

export { ConfirmDialog, useConfirmDialog };
