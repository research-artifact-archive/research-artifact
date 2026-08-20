package ltsa.lts;

import ltsa.control.ControllerGoalDefinition;
import ltsa.updatingControllers.structures.UpdateProtocolSpec;
import org.junit.Assert;
import org.testng.annotations.Test;

import java.util.List;
import java.util.Arrays;
import java.util.LinkedHashSet;

@Test(singleThreaded = true)
public class UpdatingControllersDefinitionParserTest {

    @Test
    public void revisedOnTheFlySetsBothParserFlags() {
        UpdatingControllersDefinition definition = parseDefinition(
                "updatingController UPDATEREVISED = { revised_on_the_fly }",
                "UPDATEREVISED");

        Assert.assertTrue(definition.isRevisedOnTheFly());
        Assert.assertTrue(definition.isOTF());
    }

    @Test
    public void legacyOnTheFlyDoesNotSetRevisedFlag() {
        UpdatingControllersDefinition definition = parseDefinition(
                "updatingController UPDATELEGACY = { on_the_fly }",
                "UPDATELEGACY");

        Assert.assertTrue(definition.isOTF());
        Assert.assertFalse(definition.isRevisedOnTheFly());
    }

    @Test
    public void parsesContextualUpdatePrecedenceWithoutChangingLegacyOptions() {
        UpdatingControllersDefinition definition = parseDefinition(
                "updatingController UPDATEPRECEDENCE = { revised_on_the_fly, fine_grained, "
                        + "precedence = { stopOldSpec_P_OLD < reconfigure_ENV, "
                        + "reconfigure_ENV < startNewSpec_P_NEW } }",
                "UPDATEPRECEDENCE");

        List<UpdateProtocolSpec.PrecedenceEdge> edges =
                definition.getUpdatePrecedenceEdges();
        Assert.assertEquals(2, edges.size());
        Assert.assertEquals("stopOldSpec_P_OLD", edges.get(0).before());
        Assert.assertEquals("reconfigure_ENV", edges.get(0).after());
        Assert.assertEquals("reconfigure_ENV", edges.get(1).before());
        Assert.assertEquals("startNewSpec_P_NEW", edges.get(1).after());
        Assert.assertTrue(definition.isRevisedOnTheFly());
        Assert.assertTrue(definition.isFineGrained());

        ControllerGoalDefinition oldGoal = new ControllerGoalDefinition("OLD");
        oldGoal.addSafetyDefinition(
                new Symbol(Symbol.UPPERIDENT, "P_OLD"));
        ControllerGoalDefinition newGoal = new ControllerGoalDefinition("NEW");
        newGoal.addSafetyDefinition(
                new Symbol(Symbol.UPPERIDENT, "P_NEW"));
        UpdateProtocolSpec protocol = UpdateProtocolSpec.forFineGrained(
                oldGoal, newGoal);
        protocol.registerReconfigure(0, "reconfigure_ENV");
        definition.applyUpdatePrecedence(protocol);
        Assert.assertEquals(2, protocol.getPrecedenceEdges().size());
    }

    @Test
    public void revisedOnTheFlyRecordsExplicitNewController() {
        UpdatingControllersDefinition definition = parseDefinition(
                "updatingController UPDATENEWCONTROLLER = { "
                        + "newController = NEW_C, revised_on_the_fly }",
                "UPDATENEWCONTROLLER");

        Assert.assertTrue(definition.hasExplicitNewController());
        Assert.assertEquals("NEW_C", definition.getNewController().toString());
    }

    @Test
    public void parsesArbitraryLoadableNewEndpointSubset() {
        UpdatingControllersDefinition definition = parseDefinition(
                "updatingController UPDATELOADABLE = { "
                        + "revised_on_the_fly, fine_grained, "
                        + "loadable_new_states = {0, 2, 5} }",
                "UPDATELOADABLE");

        Assert.assertTrue(definition.hasLoadableNewEndpointStateIndices());
        Assert.assertEquals(
                new LinkedHashSet<Integer>(Arrays.asList(0, 2, 5)),
                definition.getLoadableNewEndpointStateIndices());
    }

    @Test
    public void revisedOnTheFlyRejectsSelectiveFineGrainedBeforeInputPreparation() {
        LTSCompiler compiler = compile(
                "updatingController UPDATESELECTIVE = { "
                        + "revised_on_the_fly, selective_fine_grained }");

        try {
            compiler.continueCompilation("UPDATESELECTIVE");
            Assert.fail("Expected revised/selective mode validation to fail");
        } catch (LTSException expected) {
            Assert.assertEquals(
                    "revised_on_the_fly and selective_fine_grained cannot be used together.",
                    expected.getMessage());
        }
    }

    @Test
    public void fineGrainedMappingRejectsAnUnreachableTargetLabel() {
        String source = String.join("\n",
                "set C = {idle}",
                "OLD = (idle -> OLD).",
                "NEW = (idle -> NEW), UNREACHABLE = (idle -> UNREACHABLE).",
                "relation R = {OLD@OLD = reconfigure_COMPONENT -> UNREACHABLE@NEW}",
                "controllerSpec OLD_SPEC = { controllable = {C} }",
                "controller ||OLD_CONTROLLER = OLD~{OLD_SPEC}.",
                "controllerSpec NEW_SPEC = { controllable = {C} }",
                "controller ||NEW_CONTROLLER = NEW~{NEW_SPEC}.",
                "updatingController UPDATE = {",
                "oldController = OLD_CONTROLLER,",
                "newController = NEW_CONTROLLER,",
                "oldEnvironment = {OLD},",
                "newEnvironment = {NEW},",
                "mapRelation = {R},",
                "oldGoal = OLD_SPEC,",
                "newGoal = NEW_SPEC,",
                "nonblocking, revised_on_the_fly, fine_grained",
                "}",
                "||TARGET = UPDATE.");
        LTSCompiler compiler = compile(source);
        try {
            compiler.continueCompilation("TARGET");
            Assert.fail("Expected an unreachable relation endpoint to fail");
        } catch (LTSException expected) {
            Assert.assertTrue(expected.getMessage().contains(
                    "references an unknown or unreachable state label"));
            Assert.assertTrue(expected.getMessage().contains(
                    "OLD -> UNREACHABLE"));
        }
    }

    private UpdatingControllersDefinition parseDefinition(String source, String name) {
        CompositionExpression expression = compile(source).getComposites().get(name);
        Assert.assertTrue(expression instanceof UpdatingControllersDefinition);
        return (UpdatingControllersDefinition) expression;
    }

    private LTSCompiler compile(String source) {
        LTSCompiler compiler = new LTSCompiler(
                new LTSInputString(source),
                new EmptyLTSOuput(),
                ".");
        compiler.compile();
        return compiler;
    }
}
