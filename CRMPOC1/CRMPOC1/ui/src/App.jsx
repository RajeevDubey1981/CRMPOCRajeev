import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import Layout from "./layout/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import VendorDashboard from "./pages/VendorDashboard.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import ComplaintList from "./pages/complaints/ComplaintList.jsx";
import ComplaintCreate from "./pages/complaints/ComplaintCreate.jsx";
import ComplaintDetail from "./pages/complaints/ComplaintDetail.jsx";
import InstallationList from "./pages/installations/InstallationList.jsx";
import InstallationCreate from "./pages/installations/InstallationCreate.jsx";
import InstallationDetail from "./pages/installations/InstallationDetail.jsx";
import BulkInstallationWorkflowPage from "./pages/installations/BulkInstallationWorkflowPage.jsx";
import CallList from "./pages/calls/CallList.jsx";
import CallCreate from "./pages/calls/CallCreate.jsx";
import CallDetail from "./pages/calls/CallDetail.jsx";
import PendingFollowUps from "./pages/calls/PendingFollowUps.jsx";
import Calendar from "./pages/calls/Calendar.jsx";
import UserList from "./pages/admin/UserList.jsx";
import RoleList from "./pages/admin/RoleList.jsx";
import Permissions from "./pages/admin/Permissions.jsx";
import PaymentHistory from "./pages/admin/PaymentHistory.jsx";
import ProjectList from "./pages/projects/ProjectList.jsx";
import ProjectDetail from "./pages/projects/ProjectDetail.jsx";
import ItemMasterList from "./pages/item_masters/ItemMasterList.jsx";
import ItemMasterCreate from "./pages/item_masters/ItemMasterCreate.jsx";
import ItemMasterDetail from "./pages/item_masters/ItemMasterDetail.jsx";
import CourierList from "./pages/couriers/CourierList.jsx";
import CourierCreate from "./pages/couriers/CourierCreate.jsx";
import CourierDetail from "./pages/couriers/CourierDetail.jsx";
import MarketDashboard from "./pages/market/MarketDashboard.jsx";
import MarketUsers from "./pages/market/MarketUsers.jsx";
import MarketItems from "./pages/market/MarketItems.jsx";
import MarketOrders from "./pages/market/MarketOrders.jsx";
import MarketCategories from "./pages/market/MarketCategories.jsx";
import ClaimList from "./pages/claims/ClaimList.jsx";
import ClaimCreate from "./pages/claims/ClaimCreate.jsx";
import ClaimDetail from "./pages/claims/ClaimDetail.jsx";
import OrderList from "./pages/orders/OrderList.jsx";
import OrderCreate from "./pages/orders/OrderCreate.jsx";
import OrderDetail from "./pages/orders/OrderDetail.jsx";
import SerialDetails from "./pages/SerialDetails.jsx";
import SerialHistory from "./pages/serials/SerialHistory.jsx";
import ServiceRequestList from "./pages/services/ServiceRequestList.jsx";
import ServiceRequestCreate from "./pages/services/ServiceRequestCreate.jsx";
import ServiceRequestDetail from "./pages/services/ServiceRequestDetail.jsx";
import EngineerAssignedUnits from "./pages/services/EngineerAssignedUnits.jsx";
import ServiceDocumentUploadPublic from "./pages/services/ServiceDocumentUploadPublic.jsx";
import PartnerRegistrationList from "./pages/partners/PartnerRegistrationList.jsx";
import PartnerRegistrationReview from "./pages/partners/PartnerRegistrationReview.jsx";
import PartnerRegistrationPublic from "./pages/partners/PartnerRegistrationPublic.jsx";
import PartnerAgreementSign from "./pages/partners/PartnerAgreementSign.jsx";
import BidsHome from "./pages/bids/BidsHome.jsx";
import BidForm from "./pages/bids/BidForm.jsx";
import BidDetail from "./pages/bids/BidDetail.jsx";
import BidAllocation from "./pages/bids/BidAllocation.jsx";
import BidRequests from "./pages/bids/BidRequests.jsx";
import QueriesPage from "./pages/queries/QueriesPage.jsx";
import BidStats from "./pages/bids/BidStats.jsx";
import VendorRequest from "./pages/bids/VendorRequest.jsx";
import BidCalendar from "./pages/bids/BidCalendar.jsx";
import SalesRoutes from "./pages/sales/SalesRoutes.jsx";
import { isOperationsAdminRole, isSubAdminRole, isSystemAdminRole } from "./utils/roles.js";

function OperationsAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isOperationsAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function SystemAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isSystemAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

// Users page: Admin, and Sub Admin (which may only manage normal users - the server enforces that).
function UserAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isSystemAdminRole(user?.role) && !isSubAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function PermissionRoute({ module, action = "can_view", children }) {
  const { user } = useAuth();
  if (isSystemAdminRole(user?.role)) {
    return children;
  }
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const allowed = permissions.some((permission) => permission.module === module && permission[action]);
  if (!allowed) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

// Bids: the bid team (admin, sub admin, or a user ticked "Can manage bids") and vendors see different pages.
function BidsRoute({ side, children }) {
  const { user } = useAuth();
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const bids = permissions.find((p) => p.module === "bids" && !p.sub_module);
  const view = !!bids?.can_view;
  const manager = view && !!bids?.can_edit;
  const allowed = side === "manager" ? manager : side === "vendor" ? view && !manager : view;
  if (!allowed) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function DefaultLanding() {
  const { user } = useAuth();
  if (user?.role === "vendor") {
    return <Navigate to="/vendor-dashboard" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

function DashboardRoute() {
  const { user } = useAuth();
  if (user?.role === "vendor") {
    return <VendorDashboard />;
  }
  return <Dashboard />;
}

function LegacyPartnerRegistrationReviewRedirect() {
  const { id } = useParams();
  return <Navigate to={`/partner-registrations/${id}/review`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/partner-registration/:token" element={<PartnerRegistrationPublic />} />
      <Route path="/partner-agreement/:token" element={<PartnerAgreementSign />} />
      <Route path="/services/public-upload/:token" element={<ServiceDocumentUploadPublic />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DefaultLanding />} />
        <Route path="/dashboard" element={<DashboardRoute />} />
        <Route path="/vendor-dashboard" element={<VendorDashboard />} />
        <Route path="/calls" element={<PermissionRoute module="calls"><CallList /></PermissionRoute>} />
        <Route path="/calls/new" element={<PermissionRoute module="calls" action="can_create"><CallCreate /></PermissionRoute>} />
        <Route path="/calls/pending-follow-ups" element={<PermissionRoute module="calls"><PendingFollowUps /></PermissionRoute>} />
        <Route path="/calls/calendar" element={<PermissionRoute module="calls"><Calendar /></PermissionRoute>} />
        <Route path="/calls/:id" element={<PermissionRoute module="calls"><CallDetail /></PermissionRoute>} />
        <Route path="/admin/users" element={<UserAdminRoute><UserList /></UserAdminRoute>} />
        <Route path="/admin/roles" element={<SystemAdminRoute><RoleList /></SystemAdminRoute>} />
        <Route path="/admin/permissions" element={<SystemAdminRoute><Permissions /></SystemAdminRoute>} />
        <Route path="/admin/payments" element={<PermissionRoute module="payments"><PaymentHistory /></PermissionRoute>} />
        <Route path="/admin/partner-registrations" element={<Navigate to="/partner-registrations" replace />} />
        <Route path="/admin/partner-registrations/:id/review" element={<LegacyPartnerRegistrationReviewRedirect />} />
        <Route path="/complaints" element={<PermissionRoute module="complaints"><ComplaintList /></PermissionRoute>} />
        <Route path="/complaints/new" element={<PermissionRoute module="complaints" action="can_create"><ComplaintCreate /></PermissionRoute>} />
        <Route path="/complaints/:id" element={<PermissionRoute module="complaints"><ComplaintDetail /></PermissionRoute>} />
        <Route path="/services" element={<PermissionRoute module="services"><ServiceRequestList /></PermissionRoute>} />
        <Route path="/partner-registrations" element={<PermissionRoute module="partner_registrations"><PartnerRegistrationList /></PermissionRoute>} />
        <Route path="/partner-registrations/:id/review" element={<PermissionRoute module="partner_registrations"><PartnerRegistrationReview /></PermissionRoute>} />
        <Route path="/services/my-units" element={<EngineerAssignedUnits />} />
        <Route path="/services/new" element={<PermissionRoute module="services" action="can_create"><ServiceRequestCreate /></PermissionRoute>} />
        <Route path="/services/:id" element={<PermissionRoute module="services"><ServiceRequestDetail /></PermissionRoute>} />
        <Route path="/items" element={<PermissionRoute module="items"><ItemMasterList /></PermissionRoute>} />
        <Route path="/items/new" element={<PermissionRoute module="items" action="can_create"><ItemMasterCreate /></PermissionRoute>} />
        <Route path="/items/:id" element={<PermissionRoute module="items"><ItemMasterDetail /></PermissionRoute>} />
        <Route path="/couriers" element={<OperationsAdminRoute><CourierList /></OperationsAdminRoute>} />
        <Route path="/couriers/new" element={<OperationsAdminRoute><CourierCreate /></OperationsAdminRoute>} />
        <Route path="/couriers/:id" element={<OperationsAdminRoute><CourierDetail /></OperationsAdminRoute>} />
        <Route path="/orders" element={<PermissionRoute module="orders"><OrderList /></PermissionRoute>} />
        <Route path="/orders/new" element={<PermissionRoute module="orders" action="can_create"><OrderCreate /></PermissionRoute>} />
        <Route path="/orders/:id" element={<PermissionRoute module="orders"><OrderDetail /></PermissionRoute>} />
        <Route path="/installations" element={<PermissionRoute module="installations"><InstallationList /></PermissionRoute>} />
        <Route path="/installations/new" element={<PermissionRoute module="installations" action="can_create"><InstallationCreate /></PermissionRoute>} />
        <Route path="/installations/bulk-workflow" element={<PermissionRoute module="installations"><BulkInstallationWorkflowPage /></PermissionRoute>} />
        <Route path="/installations/:id" element={<PermissionRoute module="installations"><InstallationDetail /></PermissionRoute>} />
        <Route path="/claims" element={<PermissionRoute module="claims"><ClaimList /></PermissionRoute>} />
        <Route path="/claims/new" element={<PermissionRoute module="claims" action="can_create"><ClaimCreate /></PermissionRoute>} />
        <Route path="/claims/:id" element={<PermissionRoute module="claims"><ClaimDetail /></PermissionRoute>} />
        <Route path="/sales/*" element={<PermissionRoute module="sales"><SalesRoutes /></PermissionRoute>} />
        <Route path="/queries" element={<QueriesPage />} />
        <Route path="/queries/:id" element={<QueriesPage />} />
        <Route path="/bids" element={<BidsRoute><BidsHome /></BidsRoute>} />
        <Route path="/bids/new" element={<BidsRoute side="manager"><BidForm /></BidsRoute>} />
        <Route path="/bids/allocation" element={<BidsRoute side="manager"><BidAllocation /></BidsRoute>} />
        <Route path="/bids/requests" element={<BidsRoute side="manager"><BidRequests /></BidsRoute>} />
        <Route path="/bids/request" element={<BidsRoute side="vendor"><VendorRequest /></BidsRoute>} />
        <Route path="/bids/stats" element={<BidsRoute><BidStats /></BidsRoute>} />
        <Route path="/bids/calendar" element={<BidsRoute><BidCalendar /></BidsRoute>} />
        <Route path="/bids/:id/edit" element={<BidsRoute side="manager"><BidForm /></BidsRoute>} />
        <Route path="/bids/:id" element={<BidsRoute><BidDetail /></BidsRoute>} />
        <Route path="/market-admin/dashboard" element={<MarketDashboard />} />
        <Route path="/market-admin/users" element={<MarketUsers />} />
        <Route path="/market-admin/items" element={<MarketItems />} />
        <Route path="/market-admin/orders" element={<MarketOrders />} />
        <Route path="/market-admin/categories" element={<MarketCategories />} />
        <Route path="/market-admin/vendors" element={<Placeholder title="Vendor Registrations" />} />
        <Route path="/market-admin/media" element={<Placeholder title="Media Manager" />} />
        <Route path="/projects" element={<ProjectList />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/serials/details" element={<SerialDetails />} />
        <Route path="/serials/history" element={<OperationsAdminRoute><SerialHistory /></OperationsAdminRoute>} />
      </Route>
      <Route path="*" element={<DefaultLanding />} />
    </Routes>
  );
}
