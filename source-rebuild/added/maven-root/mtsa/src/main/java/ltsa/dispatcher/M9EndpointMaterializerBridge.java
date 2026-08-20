package ltsa.dispatcher;

import ltsa.lts.M9EndpointPreparedCase;
import ltsa.updatingControllers.export.M9EndpointReceiptCore;
import ltsa.updatingControllers.export.M9EndpointReceiptBundle;

import java.io.IOException;

/**
 * Package-local worker bridge to the Dispatcher's atomic one-shot endpoint
 * operation.  The worker receives only the final published receipt descriptor;
 * no native controller, intermediate core, hook scope, or sealing capability
 * crosses this boundary.
 */
final class M9EndpointMaterializerBridge {
	private M9EndpointMaterializerBridge() {
	}

	static M9EndpointReceiptBundle.PublishedReceipt
			synthesiseValidateSealAndPublishOnce(
			M9EndpointPreparedCase preparedCase,
			M9EndpointReceiptCore.Bindings receiptBindings,
			M9EndpointReceiptBundle.PublicationTarget publicationTarget)
				throws IOException {
		return TransitionSystemDispatcher
				.synthesiseValidateSealAndPublishRegisteredM9EndpointOnce(
						preparedCase, receiptBindings,
						publicationTarget);
	}
}
