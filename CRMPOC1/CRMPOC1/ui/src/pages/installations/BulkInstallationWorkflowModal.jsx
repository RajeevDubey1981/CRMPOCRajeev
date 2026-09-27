import Modal from "../../components/Modal.jsx";
import BulkInstallationWorkflowPanel from "./BulkInstallationWorkflowPanel.jsx";

export default function BulkInstallationWorkflowModal({ rows, onClose, onSaved }) {
  return (
    <Modal open onClose={onClose} title="Bulk installation workflow" maxWidth="max-w-3xl">
      <BulkInstallationWorkflowPanel rows={rows} onSaved={onSaved} showClose onClose={onClose} />
    </Modal>
  );
}
